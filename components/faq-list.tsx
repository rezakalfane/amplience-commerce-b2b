import type { Faq } from "@/lib/content";

export function FaqItem({ faq }: { faq: Faq }) {
  return (
    <details className="group border-b border-line py-5 first:pt-1 last:border-b-0">
      <summary className="flex cursor-pointer list-none items-start justify-between gap-6 text-[1.0625rem] font-semibold leading-snug">
        {faq.question}
        <span aria-hidden className="mt-0.5 text-2xl leading-none text-slate transition-transform duration-200 group-open:rotate-45">
          +
        </span>
      </summary>
      <div className="rte mt-3 text-slate" dangerouslySetInnerHTML={{ __html: faq.answerHtml }} />
    </details>
  );
}
