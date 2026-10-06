import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { GuideView } from "@/components/guide-view";
import { getGuide } from "@/lib/content";
import { alternatesFor, isLocale } from "@/lib/i18n";

export async function generateMetadata({ params }: PageProps<"/[locale]/guides/[slug]">): Promise<Metadata> {
  const { locale, slug } = await params;
  if (!isLocale(locale)) return {};
  const guide = await getGuide(slug, locale);
  return guide ? { title: guide.title, description: guide.summary, alternates: alternatesFor(locale, `/guides/${slug}`) } : {};
}

export default async function GuidePage({ params }: PageProps<"/[locale]/guides/[slug]">) {
  const { locale, slug } = await params;
  if (!isLocale(locale)) notFound();
  const guide = await getGuide(slug, locale);
  if (!guide) notFound();
  return <GuideView guide={guide} locale={locale} />;
}
