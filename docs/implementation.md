# Implementation details

How each feature works and where to find it. Paths are relative to `storefront/`.

## 1. Data layer

### Amplience: `lib/amplience.ts`, `lib/content.ts`, `lib/markdown.ts`

- **`lib/amplience.ts`** is the Delivery API client (plain `fetch`, no SDK). `AMPLIENCE_DELIVERY_HOST` picks the
  environment: the hub's CDN (`<hub>.cdn.content.amplience.net`, published content) or virtual staging
  (`<id>.staging.bigcontent.io`, latest saved content). `CONTENT_ENV` (`production` | `preview`) is derived from it.
  - **`getByKey(key, locale)`** reads one item by **delivery key** with `depth=all&format=inlined`, so every linked
    item arrives nested, and `locale=fr-FR,en-US`, so localized fields are flattened with an English fallback.
  - **`listBySchema({ schema, where, sort }, locale)`** uses the Filter API (`POST /content/filter`) and follows the
    cursor (the API returns at most 12 per page).
  - **`imageOf(imageItem)`** turns an `image` content item into a Dynamic Imaging URL (`cdn.media.amplience.net/i/<hub>/<asset>`).
- **`lib/content.ts`** maps the raw delivery JSON to small typed objects (`Page`, `Block`, `Post`, `Guide`, `Spotlight`,
  `Faq`, `Navigation`) and exposes locale-first fetchers: `getPage(key, locale)`, `getNavigation`, `getAnnouncement`,
  `getPosts`, `getPost(slug)`, `getGuides`, `getGuide(slug)`, `getSpotlights`. `previewable()` maps *any* delivered or
  form-model item for the visualization preview ([visualizations.md](visualizations.md)).
- **`lib/markdown.ts`** renders `text` / markdown fields to HTML with `marked`; site links get the locale prefix.
- **`lib/image-loader.ts`** is the global `next/image` loader: Amplience images are resized by Dynamic Imaging
  (`?w=&q=&fmt=auto`), everything else goes through Next's optimizer.
- URLs are **delivery keys**: the key is the path without the language (`blog/<slug>`, `guides/<slug>`, `faq`).
  Keys are identical in every locale because localization is inside the item.

### BigCommerce: `lib/bigcommerce.ts`

A thin GraphQL client (`gql()`), the query fragments, and typed functions. Details in [bigcommerce.md](bigcommerce.md).

## 2. Pages

| Route | File | Data |
|---|---|---|
| `/` | `app/[locale]/page.tsx` | the Page with delivery key `home` |
| `/faq`, `/guides`, `/blog`, any new page | `app/[locale]/[...slug]/page.tsx` | the Page whose delivery key is the path |
| `/blog/[slug]` | `blog/[slug]/page.tsx` | one `blogpost` (`blog/<slug>`), its authors and text/image/video items |
| `/guides/[slug]` | `guides/[slug]/page.tsx` | one `buying-guide` (`guides/<slug>`), related FAQs, live BigCommerce products |
| `/products` | `products/page.tsx` | BigCommerce faceted search over the whole catalog |
| `/products/<category>…` | `products/[...slug]/page.tsx` | category **or** product (see below) |
| `/cart` | `cart/page.tsx` | BigCommerce cart |
| `/preview` | `app/preview/page.tsx` | any content item by id, from virtual staging (non-production only) |

### Pages and components

A **Page** (`https://content.commerce.com/page`) is a title, an SEO description, a delivery key and a stack of
**components**. `components/page-blocks.tsx` renders the stack top to bottom; adding a Page in Amplience creates a new URL
with no code change. Components an editor can stack:

| Component (schema) | Renders |
|---|---|
| `hero-banner` | headline, text, CTA and photo(s); variant `home` shows two staggered photos |
| `hero-slot` | a **slot** holding a `hero-banner` that is scheduled with Editions (see [amplience.md](amplience.md)) |
| `text` / `image` / `video` | markdown, an image, a video |
| `feature-block` | image beside title and markdown (consecutive blocks share one band) |
| `category-tiles` | the BigCommerce category mosaic |
| `spotlight-row` | product spotlights as cards with live BigCommerce price, photo and link |
| `guide-row` / `guide-listing` | three chosen guides with a link / all guides |
| `post-grid` / `post-listing` | chosen posts / all posts with search |
| `faq-section` | FAQs grouped by topic in accordions |

### The catalog catch-all route

`app/[locale]/products/[...slug]/page.tsx` serves two kinds of URL. BigCommerce paths look like
`/products/<category>/<subcategory>/<product-slug>/`, so the route rebuilds the BigCommerce path from the slug and
dispatches on depth: **one or two segments are categories, three or more are products**. If the guess is wrong the other
interpretation is tried, and `notFound()` is raised if neither resolves.

## 3. Home page

The Page with delivery key `home` drives it. Its components, in order: `hero-slot` (the scheduled home hero), `text`
(intro), `category-tiles`, three `feature-block`s, `spotlight-row` (trade favourites, enriched with BigCommerce) and
`guide-row`. Reorder or replace them in Amplience; nothing is hard-coded.

![Trade favourites](images/home-spotlights.jpg)
*Trade favourites: editorial content from Amplience with live price, photo and link from BigCommerce.*

![A value block](images/home-blocks.jpg)
*A feature block (title, copy, image, layout).*

![From the buying guides](images/home-guides.jpg)
*The guides strip: three guides, with photo, audience and read time.*

## 4. Navigation, mega menu and announcement bar

- **Header links** come from the `site-navigation` item (delivery key `site/navigation`). The link whose `href` is `/products` is replaced by the
  **mega menu**.
- **Mega menu** (`components/mega-menu.tsx`, columns built in `components/site-chrome.tsx → megaColumns`): the live
  BigCommerce category tree (top level with subcategories and product counts), localized labels and a photo per top-level
  category. Hover previews it; a click pins it open; Escape, an outside click or navigating closes it. The panel is
  absolutely positioned under the header.
- **Announcement bar**: the first linked `announcement-bar` aimed at guests (`audience` is `everyone` or `guests`);
  style `info` (ink), `promo` or `warning` (amber).
- **Footer** columns, contact details and legal line come from `site-navigation`.
- **Cart link** shows the item count by reading the cart cookie and asking BigCommerce (`CartLink`, in a `Suspense`).

![Product mega menu](images/mega-menu.jpg)
*The mega menu: five top-level categories with photos, subcategories and live product counts.*

## 5. Product listing and categories

`components/plp.tsx` renders: search box, result count, **active filter chips**, "Clear all", sort, facets, product
grid and pager. It is a plain GET `<form>`, wrapped by `components/plp-form.tsx`.

![Product listing](images/plp.jpg)
*A category with a search term and a technology filter applied: result count, chips with "Clear all", sort, facets, product grid.*

### Query parameters

| Parameter | Meaning |
|---|---|
| `q` | search text (3+ characters) |
| `brand` (repeatable) | brand entity IDs |
| `f.Technology`, `f.Voltage`, `f.Warranty` (repeatable) | attribute facet values |
| `min`, `max` | price range |
| `sort` | `featured` (default), `newest`, `best_selling`, `price_asc`, `price_desc`, `name_asc` |
| `after` / `before` | cursor pagination |

`parseCatalogParams()` reads them; `searchCatalog()` runs the query ([bigcommerce.md](bigcommerce.md)).

### Interaction model

- **Filters apply on click.** `PlpForm` listens for checkbox changes, serialises the form to a URL and calls
  `router.push(url, { scroll: false })` inside `useTransition`. The grid dims (`group-data-[pending=true]:opacity-50`)
  while the server re-renders. Without JavaScript the form still works as a normal GET form (a `<noscript>` button).
- **Search as you type** (`components/search-box.tsx`): submits 350 ms after typing stops, only for 3+ characters (or
  when emptied). One or two characters show a hint and do nothing; Enter is ignored below three.
- **Price range** (`components/price-range.tsx`): applies 700 ms after typing stops.
- **Chips and "Clear all"** are server-rendered links computed from the current parameters. Removing a chip changes the
  URL; the checkboxes, search box and price inputs then **reset themselves** to match: checkboxes via a `key` that
  includes their selected state, the search box and price range by comparing the URL value with the last value they sent.
- **Cursors reset on any filter change** (only `after`/`before` links keep them), because a cursor is valid only for the
  same filters and sort.
- Each facet shows at most **8 values** (`MAX_FACET_VALUES`), most populated first, and always keeps selected values.
- On screens narrower than 1024 px the filter panel starts **collapsed** (`components/filters-details.tsx`) so the grid is
  visible first; it stays open on desktop and without JavaScript.

![Filter sidebar](images/plp-filters.jpg)
*The filter sidebar for a category: brand, technology, voltage and warranty facets (at most 8 values each) and a price range.*

### Categories include subcategory products

A category's own product list is often empty (products sit in subcategories). The category page therefore runs the
faceted search with `categoryEntityId`, which includes all descendants, instead of reading `category.products`.

## 6. Product detail page

`ProductView` in `products/[...slug]/page.tsx`:

![Product page](images/pdp.jpg)
*The product page: gallery, brand, price with stock indicator, spotlight tagline, key specs and add to cart.*

- **Gallery** (`product-gallery.tsx`): main image + thumbnails (client state).
- **Header**: brand, name, SKU / MPN, price (sale and retail "was" price when applicable), stock indicator.
- **Spotlight join**: if a `product_spotlight` entry has `bc_product_id` equal to this product, its **tagline**, badge and
  **"Best for"** use cases appear. **Guides join**: guides whose `recommended_bc_products` contains the ID are listed.
- **Key specs** (Voltage, Capacity, CCA, Technology, Warranty) and the full **specification table** come from
  BigCommerce custom fields; names and common values are translated by `translateSpec()`.
- **Volume pricing** table renders when BigCommerce returns bulk-pricing tiers.
- **Add to cart** (`components/add-to-cart.tsx`) respects the product's min/max purchase quantity.
- **Related products** from BigCommerce's `relatedProducts`.
- **Structured data**: a `schema.org/Product` JSON-LD block (price, currency, availability, SKU, GTIN, brand, images).
- **Metadata**: title, description, Open Graph image and hreflang alternates.

![Description and specifications](images/pdp-details.jpg)
*Description, "Best for" use cases from the product spotlight, and the specification table from BigCommerce custom fields.*

## 7. Cart

- **State** lives in BigCommerce; the browser keeps only the cart ID in an httpOnly cookie `bc_cart_id` (30 days).
- **Server actions** (`app/actions/cart.ts`): `addToCartAction`, `setCartQuantityAction`, `removeFromCartAction`. Each
  creates the cart if needed, calls the BigCommerce mutation and `revalidatePath("/", "layout")` so the header badge refreshes.
- **`CartView`** (`components/cart-view.tsx`) edits optimistically:
  1. A quantity change updates the line total and the subtotal immediately.
  2. The save is debounced 500 ms per line; "Updating…" shows while anything is pending; checkout is disabled meanwhile.
  3. On success it calls `router.refresh()` to reload the server's numbers; on failure it shows an error and the server's
     numbers return on the next refresh.
  4. Removing is quantity 0 (saved immediately).
- **`QtyStepper`**: −, a typeable field (commits on blur/Enter), +; Arrow Up/Down keys; clamped to 1–999; accessible labels.
- **Checkout**: the cart's `redirectedCheckoutUrl` (BigCommerce hosted checkout) is created on each cart read.

![Cart](images/cart.jpg)
*The cart with quantity steppers: totals update instantly and save to BigCommerce after a short pause.*

## 8. Content pages

- **Blog**: the `blog` Page (hero, latest posts, all posts with search: client-side text match over title and description).
  A post page has a main column of text/image/video items plus an author sidebar, and related posts by the same author.
- **Buying guides**: guide cards; guide page with numbered steps (a true sequence), pro tips, a checklist, related FAQs and
  **recommended products** that link to product pages with live price.
- **FAQ**: grouped by `topic` (the enum value is English; `topicLabel()` shows the French label), native
  `<details>` accordions.

![A buying guide](images/guide.jpg)
*A buying guide: numbered steps, pro tips, a checklist panel and recommended products with live prices.*

![FAQ page](images/faq.jpg)
*The FAQ page: hero banner, then questions grouped by topic.*

![A blog post](images/blog-post.jpg)
*A blog post: main column plus an author card.*

## 9. Preview and real-time preview

`app/preview/` implements Amplience visualizations: a server-rendered preview of the saved item from virtual staging, and a
real-time mode that follows the content form. See [visualizations.md](visualizations.md).

## 10. Internationalization

Routing in `proxy.ts`, strings and helpers in `lib/i18n.ts`. See [i18n.md](i18n.md).

## 11. Where to change things

| I want to… | Change |
|---|---|
| Edit wording, banners, FAQs, guides, nav, or stack a new page | Amplience (no code) |
| Add a UI string | `lib/i18n.ts` (`en` and `fr` objects, type-checked to match) |
| Add a filterable attribute | `FACET_NAMES` in `lib/bigcommerce.ts` (+ French label in `SPEC_NAMES_FR`) |
| Change the mega menu | `megaColumns()` in `components/site-chrome.tsx`, `components/mega-menu.tsx` |
| Change colours, type, spacing | tokens in `app/globals.css` |
| Add a page component | a schema in `scripts/amplience/schemas.py`, a case in `block()` (`lib/content.ts`) and in `BlockView` (`components/page-blocks.tsx`) |
