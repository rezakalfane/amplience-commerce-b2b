"use server";

import { cookies } from "next/headers";
import { CONTENT_ENV, STAGING_ID } from "@/lib/amplience";
import { parsePinned, pinnedHost, VSE_COOKIE, VSE_COOKIE_EXPIRED, VSE_COOKIE_OPTIONS } from "@/lib/vse";

/** Moves the session's time preview to `ts` (unix ms), or leaves it with `null`. Preview deployments only. */
export async function setTimePreview(ts: number | null) {
  if (CONTENT_ENV === "production") throw new Error("Time preview is disabled in production");
  const jar = await cookies();
  if (ts === null) return void jar.set(VSE_COOKIE, "", VSE_COOKIE_EXPIRED);
  if (!Number.isFinite(ts)) return;
  const token = parsePinned(jar.get(VSE_COOKIE)?.value ?? "")?.token ?? process.env.AMPLIENCE_TIME_TOKEN;
  if (!token) throw new Error("AMPLIENCE_TIME_TOKEN is not set");
  jar.set(VSE_COOKIE, pinnedHost(STAGING_ID, token, ts), VSE_COOKIE_OPTIONS);
}
