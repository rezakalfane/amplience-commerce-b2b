import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { PostContent } from "@/components/page-content";
import { TimeVariants } from "@/components/time-variants";
import { getPost } from "@/lib/content";
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
  if (!(await getPost(slug, locale))) notFound();
  return <TimeVariants render={(at) => <PostContent slug={slug} locale={locale} at={at} />} />;
}
