import type { Locale } from "./i18n";

/**
 * Amplience Delivery API client (read only).
 *
 * `AMPLIENCE_DELIVERY_HOST` selects the content environment:
 *   - production: `<hub>.cdn.content.amplience.net`   (published content, CDN cached)
 *   - preview:    `<id>.staging.bigcontent.io`          (virtual staging: latest saved content, nothing to publish)
 */
const HUB = process.env.AMPLIENCE_HUB_NAME ?? "";
export const DELIVERY_HOST = process.env.AMPLIENCE_DELIVERY_HOST || `${HUB}.cdn.content.amplience.net`;
export const CONTENT_ENV: "production" | "preview" = DELIVERY_HOST.includes("staging") ? "preview" : "production";

/** URL locale -> Amplience locales, in fallback order (field-level localization falls back to English). */
export const AMP_LOCALES: Record<Locale, string> = { en: "en-US", fr: "fr-FR,en-US" };

const PARAMS = (locale: Locale) => ({ depth: "all", format: "inlined", locale: AMP_LOCALES[locale] });
const NEXT_OPTS = CONTENT_ENV === "preview" ? { cache: "no-store" as const } : { next: { revalidate: 60 } };

export const schemaId = (name: string) => `https://content.commerce.com/${name}`;

/** One content item by delivery key (e.g. `home`, `blog/my-post`), localized and with links resolved. */
export async function getByKey<T>(key: string, locale: Locale): Promise<T | undefined> {
  const qs = new URLSearchParams(PARAMS(locale));
  const res = await fetch(`https://${DELIVERY_HOST}/content/key/${key}?${qs}`, NEXT_OPTS);
  if (res.status === 404) return undefined;
  if (!res.ok) throw new Error(`Amplience ${res.status} for key "${key}"`);
  return ((await res.json()) as { content: T }).content;
}

type FilterRequest = { schema: string; where?: Record<string, string>; sort?: "DESC" | "ASC" };

/** All items of a content type (the Filter API returns at most 12 per page, so follow the cursor). */
export async function listBySchema<T>({ schema, where = {}, sort }: FilterRequest, locale: Locale): Promise<T[]> {
  const filterBy = [{ path: "/_meta/schema", value: schemaId(schema) }, ...Object.entries(where).map(([path, value]) => ({ path, value }))];
  const out: T[] = [];
  let cursor: string | undefined;
  do {
    const res = await fetch(`https://${DELIVERY_HOST}/content/filter`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filterBy,
        ...(sort ? { sortBy: { key: "default", order: sort } } : {}),
        parameters: PARAMS(locale),
        page: { size: 12, ...(cursor ? { cursor } : {}) },
      }),
      ...NEXT_OPTS,
    });
    if (!res.ok) throw new Error(`Amplience filter ${res.status} for ${schema}`);
    const body = (await res.json()) as { responses?: { content: T }[]; page?: { nextCursor?: string } };
    out.push(...(body.responses ?? []).map((r) => r.content));
    cursor = body.page?.nextCursor;
  } while (cursor);
  return out;
}

// ---------------------------------------------------------------- images
type ImageLink = { id: string; name: string; endpoint: string; defaultHost: string };
export type RawImage = { image?: ImageLink; altText?: string };

/** Published assets are always served by the media CDN (virtual staging rewrites `defaultHost` to its own domain). */
const MEDIA_HOST = "cdn.media.amplience.net";

/** Dynamic Imaging URL of an `image` content item (sized by the image loader at render time). */
export function imageOf(item?: RawImage): { url: string; alt: string } | undefined {
  const l = item?.image;
  return l ? { url: `https://${MEDIA_HOST}/i/${l.endpoint}/${encodeURIComponent(l.name)}`, alt: item?.altText ?? "" } : undefined;
}
