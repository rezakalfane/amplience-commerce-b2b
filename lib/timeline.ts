import { after } from "next/server";
import { hash } from "./hash";
import { pinnedHost } from "./vse";

/**
 * Time travel cache (preview deployments only).
 *
 * Content pinned to a moment only changes at a few instants (an Edition starting, a slot being published), so instead
 * of asking Amplience for every slider step we build a **timeline**: the content for each stretch of time between two
 * changes. It is built in the background the first time a request is seen under a time pin:
 *   1. probe the slider's range at a couple of dozen instants, left to right;
 *   2. wherever two neighbouring probes differ, bisect down to the hour to find the exact change point.
 * A gap between two probes is **resolved** as soon as it is known (both probes equal, or its bisection finished), and
 * resolved gaps are answered from memory immediately, even while the rest is still loading. The slider shows this as a
 * progress bar and the change points as markers.
 *
 * Amplience limits virtual staging to 7 requests/s (350/min, shared with every other staging read), so background
 * requests are paced (see `pace` in lib/amplience.ts). Every instant is its own host (a DNS lookup and TLS connection),
 * so one probe loads *all* requests seen so far from the same host. Changes shorter than the probe gap (about 4 weeks)
 * can be missed; a timeline expires after a few minutes.
 */
const HOUR = 3_600_000;
const DAY = 24 * HOUR;
export const RANGE = { before: 30 * DAY, after: 365 * DAY };
const SAMPLES = 15;
const CONCURRENCY = 4;
const TTL = 5 * 60_000;

type Pin = { id: string; token: string; ts: number };
/** `background` marks requests made by the timeline itself, which are rate paced. */
export type Loader = (host: string, background: boolean) => Promise<unknown>;
type State = { t: number; data: Map<string, unknown>; h: string };
type Plan = {
  keys: Set<string>;
  min: number;
  max: number;
  instants: number[];
  samples: (State | undefined)[];
  refined: (State[] | undefined)[]; // per gap: change points inside (instants[i], instants[i+1]]
  expires: number;
  complete: boolean;
};
type Env = { loaders: Map<string, Loader>; plan?: Plan; building?: boolean };
// Server Actions and page renders can load separate copies of this module (and dev reloads it), so the state is global.
const g = globalThis as unknown as { __timeTravelEnvs?: Map<string, Env> };
const envs = (g.__timeTravelEnvs ??= new Map<string, Env>());

// ---- small concurrency limiter shared by all probes
let active = 0;
const waiting: (() => void)[] = [];
async function limited<T>(task: () => Promise<T>): Promise<T> {
  if (active >= CONCURRENCY) await new Promise<void>((go) => waiting.push(go));
  active++;
  try {
    return await task();
  } finally {
    active--;
    waiting.shift()?.();
  }
}

async function retry<T>(task: () => Promise<T>, tries = 3): Promise<T> {
  for (let i = 0; ; i++) {
    try {
      return await task();
    } catch (e) {
      if (i >= tries - 1) throw e;
      await new Promise((r) => setTimeout(r, 300 * 2 ** i));
    }
  }
}

/** What a resolved gap says about `ts`, or undefined while it is still unknown. */
function lookup(plan: Plan, key: string, ts: number): unknown {
  if (!plan.keys.has(key) || plan.expires < Date.now() || ts < plan.min || ts > plan.max) return undefined;
  let i = plan.instants.length - 2;
  while (i > 0 && plan.instants[i] > ts) i--;
  const a = plan.samples[i];
  const b = plan.samples[i + 1];
  if (!a || !b) return undefined;
  if (a.h === b.h) return a.data.get(key);
  const changes = plan.refined[i];
  if (!changes) return undefined;
  let cur = a;
  for (const c of changes) {
    if (c.t <= ts) cur = c;
    else break;
  }
  return cur.data.get(key);
}

/** Content for `pin.ts`: from the timeline when its gap is resolved, else straight from Amplience (and a build starts). */
export async function timelined<T>(reqKey: string, pin: Pin, load: Loader): Promise<T> {
  const envKey = `${pin.id}|${pin.token}`;
  const env = envs.get(envKey) ?? { loaders: new Map<string, Loader>() };
  envs.set(envKey, env);
  env.loaders.set(reqKey, load);

  const hit = env.plan && lookup(env.plan, reqKey, pin.ts);
  if (hit !== undefined) return hit as T;
  schedule(env, pin);
  return retry(() => load(pinnedHost(pin.id, pin.token, pin.ts), false)) as Promise<T>;
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const covers = (env: Env) => Boolean(env.plan?.complete && env.plan.expires > Date.now() && [...env.loaders.keys()].every((k) => env.plan!.keys.has(k)));

/**
 * Build once the requests of the current render have all been registered; again if more requests turn up later.
 * The work runs inside `after()`: on Vercel a function is frozen as soon as its response is sent, so without it the
 * preload would only advance a little each time something woke the instance up.
 */
function schedule(env: Env, pin: Pin) {
  if (env.building || covers(env)) return;
  env.building = true;
  const run = async () => {
    try {
      for (let round = 0; round < 4 && !covers(env); round++) {
        await sleep(400); // let the render that triggered this register all of its requests
        for (let attempt = 0; attempt < 6; attempt++) {
          try {
            await build(env, pin);
            break;
          } catch (e) {
            // typically a rate limit: the next attempt resumes where this one stopped, after a pause
            console.error("[timeline] build interrupted:", e instanceof Error ? e.message : e);
            await sleep(4000);
          }
        }
      }
    } finally {
      env.building = false;
    }
  };
  try {
    after(run);
  } catch {
    void run(); // outside a request scope there is nothing to keep alive
  }
}

async function build(env: Env, pin: Pin) {
  const keys = [...env.loaders.keys()];
  const now = Date.now();
  // Resume an unfinished plan for the same requests (for example after a rate limit) instead of starting over.
  let plan = env.plan;
  const resumable = plan && !plan.complete && plan.expires > now && plan.keys.size === keys.length && keys.every((k) => plan!.keys.has(k));
  if (!resumable) {
    const min = now - RANGE.before - DAY;
    const max = now + RANGE.after + DAY;
    plan = {
      keys: new Set(keys),
      min,
      max,
      instants: Array.from({ length: SAMPLES }, (_, i) => Math.round((min + ((max - min) * i) / (SAMPLES - 1)) / HOUR) * HOUR),
      samples: new Array(SAMPLES).fill(undefined),
      refined: new Array(SAMPLES - 1).fill(undefined),
      expires: now + TTL,
      complete: false,
    };
    env.plan = plan; // visible at once: resolved gaps start answering while the rest loads
  }
  const p = plan!;

  // One probe = every known request against one instant's host (a single connection), a few probes at a time.
  const at = (t: number): Promise<State> =>
    limited(async () => {
      const host = pinnedHost(pin.id, pin.token, t);
      const results = await retry(() => Promise.all(keys.map((k) => env.loaders.get(k)!(host, true))));
      const data = new Map(keys.map((k, i) => [k, results[i]] as const));
      // Staging rewrites some links (images) to its own host, which carries the timestamp: blank it before comparing,
      // otherwise every instant would look different from its neighbours.
      const text = results.map((r) => JSON.stringify(r) ?? "").join("\u0001").split(host).join("");
      return { t, data, h: hash(text) };
    });

  // Change points inside (lo, hi]: bisect to the hour; a third state in the middle is found by recursing on both halves.
  const refine = async (lo: State, hi: State): Promise<State[]> => {
    if (lo.h === hi.h) return [];
    if (hi.t - lo.t <= HOUR) return [hi];
    const mid = await at(lo.t + Math.max(HOUR, Math.floor((hi.t - lo.t) / 2 / HOUR) * HOUR));
    const [a, b] = await Promise.all([refine(lo, mid), refine(mid, hi)]);
    return [...a, ...b];
  };

  const settling = new Set<number>();
  const settle = async (i: number) => {
    const a = p.samples[i];
    const b = p.samples[i + 1];
    if (!a || !b || a.h === b.h || p.refined[i] || settling.has(i)) return;
    settling.add(i);
    p.refined[i] = await refine(a, b);
  };
  const work: Promise<void>[] = [];
  await Promise.all(
    p.instants.map(async (t, i) => {
      if (!p.samples[i]) p.samples[i] = await at(t);
      // A gap can be settled as soon as both of its probes are in.
      if (i > 0) work.push(settle(i - 1));
      if (i < SAMPLES - 1) work.push(settle(i));
    }),
  );
  await Promise.all(work);
  p.complete = true;
  p.expires = Date.now() + TTL;
  console.log(`[timeline] ready in ${((Date.now() - now) / 1000).toFixed(1)}s: ${keys.length} requests per probe`);
}

/** Change points, resolved ranges and build state for this staging environment (slider markers and progress bar). */
export function timelineProgress(id: string) {
  const markers = new Set<number>();
  let building = false;
  let ranges: { from: number; to: number; done: boolean }[] = [];
  for (const [key, env] of envs) {
    if (!key.startsWith(`${id}|`)) continue;
    building ||= Boolean(env.building);
    const plan = env.plan;
    if (!plan || plan.expires < Date.now()) continue;
    plan.refined.forEach((r) => r?.forEach((c) => markers.add(c.t)));
    ranges = plan.instants.slice(0, -1).map((from, i) => {
      const a = plan.samples[i];
      const b = plan.samples[i + 1];
      return { from, to: plan.instants[i + 1], done: Boolean(a && b && (a.h === b.h || plan.refined[i])) };
    });
  }
  return { markers: [...markers].sort((a, b) => a - b), building, ranges };
}
