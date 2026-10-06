"use client";

import { useRouter } from "next/navigation";
import { useRef, useState, useTransition } from "react";
import { setTimePreview } from "@/app/actions/time-preview";
import { INTL_LOCALE, type Locale } from "@/lib/i18n";

const HOUR = 3_600_000;
const DAY = 24 * HOUR;
type Labels = Record<"title" | "hint" | "note" | "now" | "exit" | "updating" | "slider", string>;

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
  const router = useRouter();
  const [ts, setTs] = useState(initial);
  const [pending, start] = useTransition();
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const min = now - 30 * DAY;
  const max = now + 365 * DAY;

  const go = (next: number | null, delay = 250) => {
    clearTimeout(timer.current);
    timer.current = setTimeout(
      () =>
        start(async () => {
          await setTimePreview(next);
          router.refresh();
        }),
      delay,
    );
  };
  const move = (next: number) => {
    setTs(next);
    go(next);
  };

  const when = new Intl.DateTimeFormat(INTL_LOCALE[locale], { dateStyle: "full", timeStyle: "short" }).format(ts);
  return (
    <div role="region" aria-label={labels.title} className="sticky top-0 z-50 border-b-2 border-amber bg-ink text-white">
      <div className="mx-auto flex max-w-[1500px] flex-wrap items-center gap-x-6 gap-y-2 px-5 py-2.5 text-sm">
        <p className="flex items-center gap-2 font-semibold">
          <span aria-hidden className="inline-block h-2.5 w-2.5 rounded-full bg-amber" />
          {labels.title}
        </p>
        <p className="text-white/80">
          {labels.hint} <strong className="text-white">{when}</strong>
          <span className="ml-2 text-white/50">{pending ? labels.updating : labels.note}</span>
        </p>

        <div className="ml-auto flex flex-wrap items-center gap-x-4 gap-y-2">
          <input
            type="range"
            aria-label={labels.slider}
            min={min}
            max={max}
            step={HOUR}
            value={Math.min(Math.max(ts, min), max)}
            onChange={(e) => move(Number(e.target.value))}
            className="w-48 accent-[#f7b500] xl:w-72"
          />
          <input
            type="datetime-local"
            aria-label={labels.hint}
            value={toInput(ts)}
            onChange={(e) => e.target.value && move(new Date(e.target.value).getTime())}
            className="rounded-[3px] border border-white/30 bg-transparent px-2 py-1 text-white [color-scheme:dark]"
          />
          <button type="button" onClick={() => move(Date.now())} className="rounded-[3px] border border-white/30 px-3 py-1 font-medium hover:bg-white/10">
            {labels.now}
          </button>
          <button
            type="button"
            onClick={() => {
              clearTimeout(timer.current);
              start(async () => {
                await setTimePreview(null);
                router.refresh();
              });
            }}
            className="rounded-[3px] bg-amber px-3 py-1 font-semibold text-ink hover:brightness-95"
          >
            {labels.exit}
          </button>
        </div>
      </div>
    </div>
  );
}
