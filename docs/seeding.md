# Seeding and managing content from scripts

Everything in `scripts/amplience/` talks to the Amplience Management API and the GraphQL asset API with the **personal access
token** (`AMPLIENCE_PAT` in `.env.local`). The scripts use only the Python standard library and are idempotent: re-running
updates items in place (items are matched by label, assets by name).

## Files

| File | Purpose |
|---|---|
| `lib.py` | env loading, HTTP/GraphQL helpers, localized-value and link builders, the `Items` upsert/publish helper, hub ids |
| `schemas.py` | the 21 content type schemas (JSON built from small helpers) |
| `deploy_schemas.py` | creates/updates schemas, registers content types, assigns them to repositories and syncs versions |
| `assets.py` | uploads a local file to Assets > C > Commerce B2B and publishes it |
| `seed.py` | uploads images, creates every item (EN + FR) and publishes in dependency order |
| `schedule.py` | seeds the campaign calendar: an event with five scheduled editions on the home hero slot (re-running replaces it) |
| `visualizations.py` | registers the Preview / Real-time preview visualizations on content types |
| `data/` | the sample content (English and French) |
| `images/` | the 62 photos and avatars the seed uploads |

## Run order

```bash
python3 scripts/amplience/deploy_schemas.py        # 1. schemas and content types
python3 scripts/amplience/seed.py                  # 2. images, items, publish   (--no-publish to skip publishing)
python3 scripts/amplience/schedule.py              # 3. scheduled hero (optional)
python3 scripts/amplience/visualizations.py <site-url> [more urls]   # 4. preview URLs
```

## How the pieces work

- **Localized values**: `L("English", "Français")` builds `{ _meta: {schema: …localized-value}, values: [...] }`.
- **Links**: `clink("author", id)` is a content link (`_meta.schema` content-link, `contentType`, `id`); `ilink(asset)` is a DAM
  image link (`id`, `name`, `endpoint`, `defaultHost`).
- **Items** need `_meta.name` (set from the label) and `_meta.deliveryKey` for anything addressed by URL.
- **Order**: items are created leaves first (images, authors, FAQs, guides, spotlights, heroes, blocks, then pages), and
  published in that same order, because production only shows linked items that are published.
- **Assets**: upload to a temporary URL, `createOrUpdateAssetByName`, `publishAsset` (async); the asset `name` is the URL slug.
- **Asset cache**: `.assets-cache.json` remembers uploaded names so reruns skip the upload (git-ignored; delete to force).
- **Dates**: post dates are spread over 2026-01-12 → 2026-09-14.

## Common tasks

### Add a blog post
Add a tuple to `data/content.py` (`POSTS[author][i]`) and its translation to `data/content_fr_posts.py`, drop a
`post-photo-<slug>.jpg` in `images/`, run `seed.py`. Or create it in Dynamic Content: a `blogpost` with delivery key
`blog/<slug>`, `account` = `Commerce B2B`, linked `text` item(s), published.

### Add a Page
In Dynamic Content create a `page`, set its delivery key (for example `about`), stack components, publish it and its
components. It is live at `/about` and `/fr/about` with no code change. Add a header link in `site-navigation` if wanted.

### Add a buying guide / FAQ / spotlight
Same pattern: data in `data/content_extra.py` and `content_fr.py`, then `seed.py`; or create the item in the UI and add it
to a `guide-row`, `faq-section` or `spotlight-row`.

### Start over
Archive the items in the `Commerce B2B` folder (or delete the cache and let `seed.py` update them in place); schemas can be
re-pushed any time with `deploy_schemas.py`.

## Pitfalls (each of these happened)

- Content items require `_meta.name`; localized values require their own `_meta.schema`.
- The GraphQL asset API wants **global ids** (base64 `Type:uuid`) for repositories and folders, not raw UUIDs; the REST API wants raw ids.
- `createAsset` returns only an id; fetch the node afterwards for `assetId` (the UUID used in image links).
- `PATCH /content-types/<id>/schema` with an empty JSON body `{}` syncs a content type to the latest schema version; with no
  body at all it returns 400.
- Listing a folder's items uses `GET /content-repositories/<repo>/content-items?folderId=<id>`, not `/folders/<id>/content-items`.
- The Delivery Filter API caps `page.size` at 12.
- The virtual staging host rewrites image `defaultHost`; the storefront pins images to `cdn.media.amplience.net`.
