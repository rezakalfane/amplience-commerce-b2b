# Decisions

Short records of the choices that shape the project: what was decided, why, and what was rejected. Newest context last
within each theme.

## Architecture

### D1. Amplience for content, BigCommerce for commerce; keyed by ID
**Decision.** Editorial content lives in Amplience; catalog, prices, stock and carts stay in BigCommerce. Content links
to products by **product ID / SKU** (`product-spotlight.bcProductId`, `buying-guide.recommendedProducts`), resolved at
request time.
**Why.** Prices and stock must never go stale or be copied into a second system. Deleting a product only removes a card.
**Rejected.** Syncing products into Amplience (duplication and drift); storing prices in content.

### D2. Server Components first; JavaScript only for interaction
**Decision.** Pages render on the server; a handful of small Client Components (filters, cart, mega menu, gallery, real-time
preview) handle interaction.
**Why.** Fast first paint and simple data flow. Even real-time preview renders on the server (see D12).

### D3. Storefront GraphQL, not the REST Management API, for the storefront
**Decision.** Read catalog and run carts through the **Storefront GraphQL API** with a channel-scoped token.
**Why.** It respects channel visibility, customer-group rules and guest pricing, is safe on the server with a narrow
token, and supports faceted search. The Management API (admin token) is for administration only.

## Content model

### D4. A Page is a stack of components, addressed by delivery key
**Decision.** Instead of one hard-wired content type per route, a `page` item holds an ordered list of component links, and
the delivery key is the URL (`home`, `faq`, `guides`, `blog`, anything new). One catch-all route renders any Page.
**Why.** Editors can create and rearrange pages without a developer; the home page, FAQ, guides and blog index all use the
same mechanism. Detail pages (blog posts, guides) keep their own routes because they have a dedicated layout.
**Rejected.** One route and type per page (every new page needs code); a free-form JSON layout field (no validation, no preview).

### D5. UI strings in code, not in Amplience
**Decision.** Button and label text live in `lib/i18n.ts`.
**Why.** The dictionary is type-checked so a missing French string is a compile error, and there is no content type to
maintain for it.
**Consequence.** Editors cannot change UI labels without a developer; marketing copy (heroes, banners, nav) *is* in the CMS.

### D6. Enum values stay English; display is mapped
**Decision.** FAQ topics, guide audiences and spotlight badges store fixed English values and are translated for display.
**Why.** A schema `enum` is one shared list, not per-locale.
**Consequence.** Adding a choice means editing the schema and the label maps.

### D7. Category photo tiles are static
**Decision.** The five home-page category tiles use files in `public/images/categories/` with labels from `lib/i18n.ts`.
**Why.** They are brand photography and match the BigCommerce category tree one-to-one.
**Alternative later.** A `category_tile` type (or reuse `block`) if editors need to change them.

## Internationalization

### D8. English at clean URLs, French under `/fr`; rewrite, not redirect
**Decision.** `proxy.ts` rewrites unprefixed paths to `/en/…` and redirects `/en/…` to the clean URL.
**Why.** Keeps existing URLs stable for the default language while using one `[locale]` route tree.
**Rejected.** `/en` prefix for English (changes all URLs); sub-domains (needs DNS/hosting setup).

### D9. Same delivery key in every language
**Decision.** `/fr/blog/<english-slug>`: one item, one delivery key, two locales inside it.
**Why.** The language switcher is exact (swap the prefix) and field-level localization keeps both languages in one item.
**Trade-off.** Less SEO benefit than translated slugs; Amplience supports localized delivery keys if that is needed later.

### D10. Field-level localization with English fallback
**Decision.** Text fields are localizable (`values: [{ locale, value }]`) and every read asks for `locale=fr-FR,en-US`.
**Why.** One item per entity (no copies to keep in sync), and a partially translated site is better than gaps.
**Rejected.** One item per language in per-locale repositories (duplicated structure; changing an image means editing twice).
**Consequence.** The five existing hub schemas were re-versioned to make their text localizable.

### D11. Product text stays English until BigCommerce translates it
**Decision.** Do not machine-translate product names or copy in code.
**Why.** Product data belongs to BigCommerce. The client already sends `Accept-Language`, so Store Translations will light up
without code changes.

## Editing

### D12. Visualizations render on the server, including real time
**Decision.** The preview route renders React Server Components from a content id; real-time preview sends the unsaved
form model to a **server action** that returns the rendered tree.
**Why.** There is one rendering path (the live site's components), so the preview cannot drift from the site, and BigCommerce
data keeps working inside previews.
**Trade-off.** Every keystroke (debounced) is a server round trip. **Rejected:** client-side rendering from the model (a second,
parallel implementation of every page).

### D13. The preview exists only in preview deployments
**Decision.** `/preview` is a 404 and its action throws when `AMPLIENCE_DELIVERY_HOST` is not a staging host.
**Why.** Production must serve only published content and expose no way to render unpublished drafts.

### D14. No editing markup in HTML
**Decision.** Components render plain HTML with no per-field edit attributes; editors edit in the content form beside the preview.
**Why.** Smaller HTML and one rendering path for visitors and editors.

### D29. Time travel preloads a timeline of changes instead of caching per instant
**Decision.** In a time preview the server finds the instants where content changes (probe, then bisect to the hour) and keeps
one copy per stretch; gaps are usable as soon as they are known (`lib/timeline.ts`).
**Why.** Every instant is a different virtual staging host (new DNS and TLS), so caching per timestamp never hits; virtual staging
is limited to 7 requests/s, so exhaustive sampling would be throttled. Content changes at a handful of instants, so a few dozen
paced probes describe the whole year, and the same data gives markers, previous/next change and edition bands.
**Trade-off.** A change shorter than the probe gap (about four weeks) can be missed; the build takes about 25 seconds on first use.

### D30. Preloaded time states are rendered up front and switched in the browser
**Decision.** Once the timeline is complete, the server renders each stretch of time once and the browser shows the one matching
the slider (`TimeVariants`, `TimeSwitch`); the server only syncs after the user pauses.
**Why.** A server round trip per slider step (about 400 ms even when warm) feels sluggish and flickers; switching takes 10–20 ms.
**Rejected.** Transitions around each action (React batches overlapping ones and the page only updates when dragging stops);
`router.refresh()` after the action (a second render per step).

### D31. Edition names travel in the slot content
**Decision.** `hero-slot.campaign` holds the name, set by the scheduler.
**Why.** The storefront has no Management API access (and must not hold the PAT), and the Delivery API does not expose edition names.

## Catalog

### D15. A category lists its subcategories' products
**Decision.** Category pages use faceted search by `categoryEntityId` rather than `category.products`.
**Why.** Products are assigned to subcategories; the category's own list is empty, which made category pages blank.

### D16. Facets chosen by coverage, capped at 8 values
**Decision.** Brand plus Technology (93% of products), Voltage (89%), Warranty (66%); every facet shows ≤ 8 values and keeps
selected ones visible. Capacity range (54%) and Format (26%) were rejected.
**Why.** A filter that applies to a minority of products misleads. Long value lists (25 technologies) are noise.

### D17. The listing is a GET form that navigates on change
**Decision.** Filters are an HTML `<form method="get">`; JavaScript intercepts changes and calls `router.push` with
`{ scroll: false }`.
**Why.** Every state is a shareable, crawlable URL; it works without JavaScript; there is no client-side filter state to
keep in sync with the server. Chips and clear-all are plain links.
**Details.** Checkbox `key`s include their selected state and the search/price inputs reconcile with the URL, so removing a
chip resets the controls.

### D18. Search starts at 3 characters
**Decision.** Search-as-you-type is debounced (350 ms) and ignores 1–2 characters (with a hint).
**Why.** One or two characters match too broadly and cause needless requests.

## Cart

### D19. Cart state in BigCommerce; hosted checkout
**Decision.** The browser stores only the cart ID in an httpOnly cookie; checkout uses BigCommerce's hosted checkout URL.
**Why.** No payment or PII handling in this app; carts are shared with BigCommerce tooling and persist across devices only
via the cookie (guest carts).

### D20. Optimistic quantity editing
**Decision.** Update totals immediately, save after 500 ms, reconcile with `router.refresh()`.
**Why.** Quantity buttons feel instant; a failed save shows an error and the next refresh restores the server's numbers.

## Design

### D21. "Workbench": light, photographic, one accent
**Decision.** Cool steel and ink with terminal amber; Archivo + IBM Plex Sans; open product tiles; 1100 px pages.
**Why.** Fits a trade supplier (practical, legible, photography-led) and avoids the usual generated-site defaults. See
[design-system.md](design-system.md).
**Rejected.** Dark theme; cream with a warm accent; boxed shadowed cards.

### D22. Photography policy
**Decision.** Use only text-free photos from pilesbatteries.com (with the owner's permission); never bake titles into images;
guide heroes use photography, not composed product shots.
**Why.** Titles in images cannot be translated, edited or read by screen readers. Product images come from BigCommerce.

### D23. Amber is never body or heading text on white
**Decision.** Amber is for fills, underlines and rules.
**Why.** Amber on white measures 2.3:1, which fails WCAG. (Step numbers were changed from deep amber to ink after a contrast check.)

## Process

### D24. Idempotent Python scripts instead of manual entry
**Decision.** Schemas, content types, images, sample content and visualizations are all pushed through the Management and
GraphQL asset APIs by scripts in `scripts/amplience/`.
**Why.** Reproducible, reviewable and re-runnable: schema, English, translations and images are refreshed together.

### D25. Assets are replaced in place
**Decision.** Uploads use `createOrUpdateAssetByName`; the asset name is the URL slug.
**Why.** Re-running never duplicates assets, and a changed image updates every item that references it.

### D26. All sample content is fictional
**Decision.** Authors, article text, FAQ policies, delivery claims and contact details are placeholders (`example.com`).
**Why.** Nothing in the site should be mistaken for real policy or real people. Replace before launch.

### D27. Production and Preview by content environment, not by code
**Decision.** One codebase; `AMPLIENCE_DELIVERY_HOST` decides whether a deployment reads the CDN (published) or virtual
staging (saved). Vercel's Production scope reads the CDN; Preview scope (branch `staging` and all others) reads staging.
**Why.** The review step is "publish" itself: editors check the staging site or the visualizations, and only publishing
changes what visitors see. No workflow tooling to maintain.

### D28. Preview deployments are public
**Decision.** Vercel deployment protection is off for the project.
**Why.** Amplience loads the staging site inside its app; a Vercel login wall would break the visualizations. Preview pages
are `noindex` (Vercel) and carry only content that editors have already saved.

## Open questions

- Will buyers **sign in** (B2B Edition companies, price lists, quotes)? Today "your negotiated prices" is aspirational copy.
- Do we want **translated slugs** for French SEO (reverses D9)?
- Should the category tiles move into Amplience (a `category-tiles` component exists; it currently reads the BigCommerce tree)?
- Publish **webhooks and tag-based caching** for Amplience reads at production traffic.
