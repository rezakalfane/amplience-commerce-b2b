import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { AnnouncementBar, SiteFooter, SiteHeader } from "@/components/site-chrome";
import { TimePreviewBar } from "@/components/time-preview-bar";
import { getTimePreview } from "@/lib/amplience";
import { body, display } from "@/lib/fonts";
import { LOCALES, getMessages, isLocale } from "@/lib/i18n";
import "../globals.css";

export const metadata: Metadata = {
  title: { default: "Commerce B2B", template: "%s | Commerce B2B" },
  description: "A B2B storefront powered by Amplience and BigCommerce.",
};

export function generateStaticParams() {
  return LOCALES.map((locale) => ({ locale }));
}

export default async function RootLayout({ children, params }: LayoutProps<"/[locale]">) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const time = await getTimePreview();
  const t = getMessages(locale);

  return (
    <html
      lang={locale}
      className={`${display.variable} ${body.variable} h-full`}
    >
      <body className="min-h-full flex flex-col">
        {time && (
          <TimePreviewBar
            ts={time.ts}
            now={time.now}
            locale={locale}
            labels={{
              title: t.timePreview,
              hint: t.timePreviewHint,
              note: t.timePreviewNote,
              now: t.timePreviewNow,
              exit: t.timePreviewExit,
              updating: t.timePreviewUpdating,
              slider: t.timePreviewSlider,
              prev: t.timePreviewPrev,
              next: t.timePreviewNext,
            }}
          />
        )}
        <AnnouncementBar locale={locale} />
        <SiteHeader locale={locale} />
        <main className="flex-1">{children}</main>
        <SiteFooter locale={locale} />
      </body>
    </html>
  );
}
