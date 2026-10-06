import { GuideView } from "@/components/guide-view";
import { PageBlocks } from "@/components/page-blocks";
import { PostView } from "@/components/post-view";
import { AMP_LOCALES } from "@/lib/amplience";
import { previewable } from "@/lib/content";
import type { Locale } from "@/lib/i18n";
import { resolveLocalized } from "@/lib/localized";

/** Renders any delivered / form-model content item the way the live site would. */
export async function renderPreview(model: Record<string, unknown>, locale: Locale) {
  const flat = resolveLocalized(model, AMP_LOCALES[locale].split(",")) as Record<string, unknown>;
  const p = previewable(flat, locale);
  if (!p) {
    return (
      <p className="page py-16 text-slate">
        This content type has no preview. Open a Page, blog post, buying guide or page component.
      </p>
    );
  }
  switch (p.kind) {
    case "page":
      return <PageBlocks blocks={p.page.blocks} locale={locale} path="/preview" />;
    case "blocks":
      return <PageBlocks blocks={p.blocks} locale={locale} path="/preview" />;
    case "post":
      return <PostView post={p.post} locale={locale} />;
    case "guide":
      return <GuideView guide={p.guide} locale={locale} />;
  }
}
