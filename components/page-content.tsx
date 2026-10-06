import { Flash } from "@/components/flash";
import { GuideView } from "@/components/guide-view";
import { PageBlocks } from "@/components/page-blocks";
import { PostView } from "@/components/post-view";
import { getGuide, getPage, getPost, getPosts } from "@/lib/content";
import type { Locale } from "@/lib/i18n";

/**
 * The content of a route as of `at` (the time preview renders one copy per time state; `at` is undefined otherwise).
 * Each reads its own data so the route can hand them to <TimeVariants render={(at) => …} />.
 */
export async function PageContent({ pageKey, locale, path, q, at }: { pageKey: string; locale: Locale; path?: string; q?: string; at?: number }) {
  const page = await getPage(pageKey, locale, at);
  return page ? <PageBlocks blocks={page.blocks} locale={locale} path={path} q={q} at={at} /> : null;
}

export async function PostContent({ slug, locale, at }: { slug: string; locale: Locale; at?: number }) {
  const [post, all] = await Promise.all([getPost(slug, locale, at), getPosts(locale, at)]);
  if (!post) return null;
  // Related reading: the latest other articles by the same first author.
  const byAuthor = post.authors[0]?.name;
  const related = all.filter((p) => p.id !== post.id && p.authors[0]?.name === byAuthor).slice(0, 3);
  return (
    <Flash id="article" value={post}>
      <PostView post={post} related={related} locale={locale} />
    </Flash>
  );
}

export async function GuideContent({ slug, locale, at }: { slug: string; locale: Locale; at?: number }) {
  const guide = await getGuide(slug, locale, at);
  return guide ? (
    <Flash id="article" value={guide}>
      <GuideView guide={guide} locale={locale} />
    </Flash>
  ) : null;
}
