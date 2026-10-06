"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { getTimeMarkers, setTimePreview } from "@/app/actions/time-preview";
import { INTL_LOCALE, type Locale } from "@/lib/i18n";
import { timeStore } from "@/lib/time-store";

const HOUR = 3_600_000;
const DAY = 24 * HOUR;
type Labels = Record<"title" | "hint" | "note" | "now" | "exit" | "updating" | "slider" | "prev" | "next", string>;

/** `datetime-local` wants local wall-clock time without a zone. */
const toInput = (ts: number) => {
  const d = new Date(ts - new Date(ts).getTimezoneOffset() * 60_000);
  return d.toISOString().slice(0, 16);
};

/**
 * Banner shown on preview deployments while the session is pinned to a moment in time (Amplience preview apps, or
 * `?time=`). A slider and a date/time field move through time; the page's content follows live. Exit returns to
 * the latest saved content.
 */
export function TimePreviewBar({ ts: initial, locale, labels, now }: { ts: number; locale: Locale; labels: Labels; now: number }) {
  const [ts, setTs] = useState(initial);
  const [pending, setPending] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  // One request in flight at a time, always carrying the latest value. A step is only finished once the page has really
  // re-rendered for it (the `ts` prop the server hands back equals the requested time): sending the next step earlier
  // makes Next keep postponing the render, and the page would sit on the old content until dragging stops.
  const wanted = useRef<number | null | undefined>(undefined);
  const busy = useRef(false);
  const applied = useRef<{ ts: number | null; done: () => void } | undefined>(undefined);
  const latest = useRef(initial); // the time the user last asked for
  const wasReady = useRef(false);
  const { segments } = useSyncExternalStore(timeStore.subscribe, timeStore.get, timeStore.get);
  const [markers, setMarkers] = useState<number[]>([]);
  const [ranges, setRanges] = useState<{ from: number; to: number; done: boolean }[]>([]);
  const min = now - 30 * DAY;
  const max = now + 365 * DAY;

  useEffect(() => {
    if (applied.current?.ts === initial) applied.current.done();
  }, [initial]);

  const flush = () => {
    if (busy.current) return;
    if (wanted.current === undefined) return setPending(false);
    const next = wanted.current;
    wanted.current = undefined;
    busy.current = true;
    setPending(true);
    // The action rewrites the cookie, which makes Next re-render the current page in the same response (no router.refresh).
    setTimePreview(next)
      .then(() => (next === null ? undefined : new Promise<void>((done) => { applied.current = { ts: next, done }; setTimeout(done, 4000); })))
      .catch((e) => console.error("time preview failed", e))
      .finally(() => {
        applied.current = undefined;
        busy.current = false;
        flush();
      });
  };
  const commit = (next: number | null, delay: number) => {
    wanted.current = next;
    clearTimeout(timer.current);
    timer.current = setTimeout(flush, delay);
  };
  const move = (next: number) => {
    window.__timeTravelAt = Date.now(); // lets areas that appear because of this move blink too (components/change-flash.tsx)
    latest.current = next;
    setTs(next); // the label follows the thumb instantly
    timeStore.set({ ts: next }); // preloaded mode: the page switches to the matching time state right here, no request
    // The server only needs to catch up (cookie, layout, shareable URL state): quickly when it must render the content
    // itself, after a pause when the browser already shows it.
    commit(next, timeStore.get().variants ? 700 : 150);
  };

  // The server preloads every time state in the background (lib/timeline.ts); follow its progress and change points.
  const loadProgress = () =>
    getTimeMarkers()
      .then((r) => {
        setMarkers(r.markers);
        setRanges(r.ranges);
        const ready = !r.building && r.ranges.length > 0 && r.ranges.every((x) => x.done);
        // Everything is preloaded: ask the server for the page once more so it comes back with one copy per time
        // state (components/time-variants.tsx); from then on, moving the slider needs no request at all.
        if (ready && !wasReady.current && r.markers.length > 0 && !timeStore.get().variants) commit(latest.current, 0);
        wasReady.current = ready;
        return !ready;
      })
      .catch(() => false);
  // `commit` only touches refs and stable setters, so the closure captured here stays valid for the whole session.
  /* eslint-disable react-hooks/exhaustive-deps */
  useEffect(() => {
    let stop = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const poll = async () => {
      const more = await loadProgress();
      if (!stop) timer = setTimeout(poll, more ? 700 : 5000);
    };
    timer = setTimeout(poll, 600);
    return () => {
      stop = true;
      clearTimeout(timer);
    };
  }, []);
  /* eslint-enable react-hooks/exhaustive-deps */


  // Previous / next change: the start of the next stretch of content, or the end of the previous one.
  const nextChange = markers.find((m) => m > ts);
  const startOfCurrent = [...markers].reverse().find((m) => m <= ts);
  const prevChange = startOfCurrent === undefined ? undefined : Math.max(min, startOfCurrent - HOUR);
  const pct = (m: number) => (m - min) / (max - min);

  // Named stretches of time (editions / campaigns) from the preloaded page: bands above the slider, and the current name.
  const bands = segments.map((seg, i) => {
    const from = i === 0 ? min : seg.from;
    const to = segments[i + 1]?.from ?? max;
    return { ...seg, from, to, standard: i === 0 || i === segments.length - 1 };
  });
  const current = bands.filter((b) => b.from <= ts).at(-1)?.label;
  const short = new Intl.DateTimeFormat(INTL_LOCALE[locale], { day: "numeric", month: "short", year: "numeric" });
  const TONES = ["bg-amber", "bg-[#ffd25a]", "bg-[#c98f00]"];

  const when = new Intl.DateTimeFormat(INTL_LOCALE[locale], { weekday: "short", day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }).format(ts);
  return (
    <div role="region" aria-label={labels.title} className="sticky top-0 z-50 border-b-2 border-amber bg-ink text-white">
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 px-5 py-2 text-sm">
        <p className="flex items-center gap-2 whitespace-nowrap" title={labels.note}>
          <span aria-hidden className={`inline-block h-2.5 w-2.5 rounded-full bg-amber ${pending ? "animate-pulse" : ""}`} />
          <span className="font-semibold">{labels.title}</span>
          <span className="text-white/60">·</span>
          <span className="hidden text-white/70 2xl:inline">{labels.hint}</span>
          <strong className="tabular-nums">{when}</strong>
          {current && <span className="rounded-full bg-amber/20 px-2 py-0.5 text-xs font-semibold text-amber">{current}</span>}
          <span className="hidden text-white/50 min-[1900px]:inline">· {labels.note}</span>
        </p>

        <div className="flex flex-wrap items-center gap-x-2.5 gap-y-2">
          <button type="button" aria-label={labels.prev} title={labels.prev} disabled={prevChange === undefined} onClick={() => prevChange !== undefined && move(prevChange)} className="rounded-[3px] border border-white/30 px-2 py-1 leading-none hover:bg-white/10 disabled:opacity-30">
            ‹
          </button>
          <div className="relative flex items-center pt-3.5">
            {/* Preload progress: stretches of time whose content is already known are amber */}
            <div aria-hidden className="pointer-events-none absolute inset-x-2 top-[calc(50%+7px)] h-1 -translate-y-1/2 overflow-hidden rounded-full bg-white/15">
              {ranges.map((r) => {
                const from = Math.min(1, Math.max(0, pct(r.from)));
                const to = Math.min(1, Math.max(0, pct(r.to)));
                return (
                  <span
                    key={r.from}
                    className={`absolute inset-y-0 transition-colors duration-500 ${r.done ? "bg-amber" : ""}`}
                    style={{ left: `${from * 100}%`, width: `${(to - from) * 100}%` }}
                  />
                );
              })}
            </div>
            {/* Editions / campaigns: one band per stretch of time between two content changes (hover for the name) */}
            {bands.length > 0 && (
              <div className="absolute inset-x-2 top-0 h-2.5">
                {bands.map((b, i) => {
                  const from = Math.min(1, Math.max(0, pct(b.from)));
                  const to = Math.min(1, Math.max(0, pct(b.to)));
                  const active = b.from <= ts && ts < b.to;
                  return (
                    <span
                      key={`${b.from}-${i}`}
                      title={`${b.label ?? "–"} · ${b.standard && i === 0 ? "…" : short.format(b.from)} → ${i === bands.length - 1 ? "…" : short.format(b.to)}`}
                      className={`absolute inset-y-0 rounded-[1px] border-r border-ink transition-opacity ${b.standard ? "bg-white/40" : TONES[i % TONES.length]} ${active ? "opacity-100" : "opacity-50 hover:opacity-90"}`}
                      style={{ left: `${from * 100}%`, width: `${(to - from) * 100}%` }}
                    />
                  );
                })}
              </div>
            )}
            <input
              type="range"
              aria-label={labels.slider}
              min={min}
              max={max}
              step={HOUR}
              value={Math.min(Math.max(ts, min), max)}
              onChange={(e) => move(Number(e.target.value))}
              className="time-slider relative w-40 lg:w-48 xl:w-64 2xl:w-72"
            />
            {markers
              .filter((m) => m > min && m < max)
              .map((m) => (
                <span
                  key={m}
                  aria-hidden
                  title={new Date(m).toLocaleString(INTL_LOCALE[locale])}
                  className="pointer-events-none absolute top-[calc(50%+7px)] h-3.5 w-[2px] -translate-y-1/2 rounded-full bg-white/80"
                  style={{ left: `calc(8px + (100% - 16px) * ${pct(m)})` }}
                />
              ))}
          </div>
          <button type="button" aria-label={labels.next} title={labels.next} disabled={nextChange === undefined} onClick={() => nextChange !== undefined && move(nextChange)} className="rounded-[3px] border border-white/30 px-2 py-1 leading-none hover:bg-white/10 disabled:opacity-30">
            ›
          </button>
          <input
            type="datetime-local"
            aria-label={labels.hint}
            value={toInput(ts)}
            onChange={(e) => e.target.value && move(new Date(e.target.value).getTime())}
            className="rounded-[3px] border border-white/30 bg-transparent px-1.5 py-1 text-xs text-white [color-scheme:dark]"
          />
          <button type="button" onClick={() => move(Date.now())} className="whitespace-nowrap rounded-[3px] border border-white/30 px-3 py-1 font-medium hover:bg-white/10">
            {labels.now}
          </button>
          <button type="button" onClick={() => commit(null, 0)} className="whitespace-nowrap rounded-[3px] bg-amber px-3 py-1 font-semibold text-ink hover:brightness-95">
            {labels.exit}
          </button>
        </div>
      </div>
    </div>
  );
}
