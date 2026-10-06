import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { PostView } from "@/components/post-view";
import { getPost, getPosts } from "@/lib/content";
import { alternatesFor, isLocale } from "@/lib/i18n";

export async function generateMetadata({ params }: PageProps<"/[locale]/blog/[slug]">): Promise<Metadata> {
  const { locale, slug } = await params;
  if (!isLocale(locale)) return {};
  const post = await getPost(slug, locale);
  return post ? { title: post.title, description: post.description, alternates: alternatesFor(locale, `/blog/${slug}`) } : {};
}

export default async function PostPage({ params }: PageProps<"/[locale]/blog/[slug]">) {
  const { locale, slug } = await params;
  if (!isLocale(locale)) notFound();
  const [post, all] = await Promise.all([getPost(slug, locale), getPosts(locale)]);
  if (!post) notFound();
  // Related reading: the latest other articles by the same first author.
  const byAuthor = post.authors[0]?.name;
  const related = all.filter((p) => p.id !== post.id && p.authors[0]?.name === byAuthor).slice(0, 3);
  return <PostView post={post} related={related} locale={locale} />;
}
