# History

A chronological record of every request made while building this storefront, and what came out of it.
Prompts are quoted or condensed from the conversation; "Screenshot" means the request came with an image of the
browser. Dates are 2026.

> Conventions: **Result** is a summary of what was actually delivered. Things that were investigated and
> rejected, or that turned out different from the first attempt, are called out because they explain later decisions.

---

## 6 October

### 1. Start from the existing demo, on Amplience
**Prompt:** "Create the same demo (same UI, components, Next.js stack) but integrated to Amplience. I have a Personal Access
Token (PAT) which should be enough to create Content Type Schemas, Content Types, and Content (folder C > Commerce B2B).
Existing schemas to use: blogpost, video, image, text, author. The other ones need to be created. Remove all code related to
the previous CMS (UI, API calls, live-preview tags). Same Vercel concept with Production / Preview on a new deployment
amplience-commerce-b2b. Use slots for content scheduling, maybe for a home hero banner. Create the concept of Page where you
can stack things. Use delivery key for URLs. Upload images in Content if possible."

**Result:** Copied the storefront (without dependencies, build output, git history or secrets) into a new project and kept
the BigCommerce side untouched. Asked for the hub name and PAT to be put in `.env.local` rather than the chat; confirmed the
PAT works as a bearer token against both the Management API and the GraphQL asset API.

### 2. Discovery of the hub
**Result:** Found the hub `commercedemo` (locales `en-US` and `fr-FR`, virtual staging host), the `content` and `slots`
repositories, the `C > Commerce B2B` content and asset folders, and the five existing schemas. They were not localizable and
`blogpost.account` only allowed `Microsoft` / `Colgate`.

### 3. "Can we make the content types localizable?"
**Result:** Amplience supports field-level localization (`values: [{ locale, value }]`, delivery `locale=fr-FR,en-US`).
Options were presented (localizable twins, re-version the existing five, or one item per language). **Decision:** re-version
the existing five ("these items are old demo ones"); they stay in the hub for the admin UI but are not used. `account` gained
`Commerce B2B`. Rejected: per-language items with prefixed delivery keys (duplicated structure).

### 4. Content model and schemas
**Result:** Designed 21 schemas (`scripts/amplience/schemas.py`): a **Page** stacking components (hero banner, hero slot,
feature block, text/image/video, category tiles, spotlight / guide / post rows and listings, FAQ section), plus buying guide,
product spotlight, FAQ, announcement bar and site navigation. `deploy_schemas.py` pushes schemas, registers content types and
syncs versions. The hero slot is a schema with validation level *Slot* in the `slots` repository.

### 5. Assets and content
**Prompt (mid-turn):** "Asset upload worked btw" / "one is a duplicate".
**Result:** Images upload through a temporary upload URL, `createOrUpdateAssetByName` and `publishAsset`. A test asset left in
the folder was deleted. `seed.py` uploaded 62 images and created and published ~190 items (36 posts, 6 guides, 15 FAQs, 6
spotlights, navigation, heroes, pages), English and French. Verified through the Delivery API: key lookup, localization with
English fallback, deep inlining and the slot content.

### 6. The storefront on Amplience
**Result:** Replaced the old SDK with a small Delivery API client (`lib/amplience.ts`), typed mappers (`lib/content.ts`),
markdown rendering and a Dynamic Imaging image loader. Home, FAQ, guides and blog index became Pages rendered by one block
renderer; `[...slug]` serves any new Page by delivery key. Removed all previous-CMS code, edit tags, packages and scripts.
Compared full-page screenshots with the original design.

### 7. "We'll need to adapt the storefront so it supports preview and real time preview"
**Result:** Added `app/preview` (visualization entry point reading virtual staging by content id) and a real-time mode that
follows the content form with `dc-visualization-sdk` and re-renders on the server through a server action. Verified the render
path with an unsaved French title. 404 in production by design. See [docs/visualizations.md](docs/visualizations.md).

### 8. "We can also remove what is [previous-CMS] related in the HISTORY.md? And in general in the repo"
**Result:** Rewrote this file, the README and every document for Amplience; deleted the old scripts, workflow and screenshots;
re-rendered the architecture diagram.

### 9. "Connect Vercel to Git?"
**Result:** Created the Vercel project `amplience-commerce-b2b` (Production reads the CDN, Preview reads virtual staging),
fixed the Next.js framework preset, and connected it to a GitHub repository with `main` (production) and `staging` (preview).

### 10. Scheduling, visualizations and the Git hand-off
**Result:** `schedule.py` creates an event with two Editions on the `home-hero` slot (a winter hero from 15 Nov 2026, back to the
standard hero on 5 Jan 2027); edition slot content links to **snapshots** (`_meta.rootContentItemId`). `visualizations.py` registers
*Preview* and *Real-time preview* on the previewable content types. Pushed `main` and `staging` to a private GitHub repository
and connected Vercel (Production from `main`, Preview from `staging`); preview deployments are public so Amplience can frame them.

### 11. "Be sure to use my rezakalfane GitHub account for all commit"
**Result:** The repository now commits as the `rezakalfane` GitHub identity (noreply address). The first two commits used the work
email, and Vercel did not start builds for them; new commits use the right identity.

### 12. "Should we update the hub properties? also failing" (screenshots)
**Result:** Two fixes. (1) Real-time preview connected but showed "no preview": the form model from the SDK can arrive wrapped in
`{ content }` and without a root `_meta.schema`, so the server action now unwraps it, falls back to the saved item's schema and, if
a model is still unrecognised, prints the schema and fields it received. (2) Hub **Preview applications**: the storefront accepts
`?vse=<domain>` on preview deployments (stored in a cookie by `proxy.ts`) so Scheduling and Edition previews show the whole site at
that date. The hub setting itself must be added in the UI (the API needs the DAM publishing secret); see
[docs/visualizations.md](docs/visualizations.md).

### 13. "Should we have a nice banner stating that it's a time preview, with a date/time control to travel in time (a slider?) live, and exit?"
**Prompt (screenshot):** the staging site opened from a Scheduling preview app, showing the winter hero.
**Result:** A sticky **Time preview** banner on preview deployments while the session is pinned to a moment: slider, date/time
field, Now and Exit; content re-renders live. Time travel works because the pinned staging domain's timestamp can be swapped
(`<id>-<token>-<unix ms>`); the token is not date-dependent but cannot be invented, so entry via `?time=` uses
`AMPLIENCE_TIME_TOKEN` (set in Vercel Preview) and Amplience-provided sessions reuse their own. Two bugs found by testing in a
browser: Server Action posts re-ran the proxy and re-applied a stale `?time=` (fixed by consuming the parameter with a redirect),
and a partitioned cookie is only cleared by repeating its attributes. Verified: standard hero now, winter hero between 15 Nov 2026
and 5 Jan 2027, standard hero again afterwards.

### 14. "Screen can flicker while sliding" / "compact the date/time display"
**Result:** Moves are now sent one at a time and the banner waits for the new time to arrive before sending the next; the date is a
single compact line. Root causes found by logging DOM changes in a browser: overlapping React transitions are batched (the page only
updated when dragging stopped) and `router.refresh()` after a cookie-setting action rendered every step twice.

### 15. "A short blinking dotted border for areas that changed when time traveling"
**Result:** Every page component, the announcement bar and article pages are wrapped in `<Flash id value>`; a content hash is compared
with the last one seen for that area and changed areas blink with a dotted amber outline for about two seconds.

### 16. "Temporarily preload/cache content for the time travel to make it super fast", "color the slider like a progress bar", "no need to reload the page each time?"
**Prompt (link):** the Amplience API limits page.
**Result:** `lib/timeline.ts` preloads the whole year: probe, bisect, resolve gaps progressively, with the slider filled as a progress bar,
markers at each change and previous/next change buttons. Virtual staging allows 7 requests/s, so probing is paced, backs off on 429 and resumes.
A bug found by logging: staging rewrites image hosts (which contain the timestamp), so every probe looked different until that text was blanked
before comparing. Then **instant mode**: the page is rendered once per time state and the browser switches between them in 10-20 ms with no request.

### 17. "Add a couple more changes in the scheduled slot" and "an overlay on the slider timeline to show editions"
**Prompt (screenshots):** the event, an edition, the date/time preview dialog and the scheduling timeline, copied into `docs/images`.
**Result:** The schedule now has five editions (winter check, trade deals week, winter check again, holiday delivery cut-off, back to
standard), with two new hero banners. `hero-slot.campaign` carries each edition's name so the slider can show one named band per edition
(hover for dates) and the current name next to the date.

### 18. "Everything in one row", "preview doesn't show the edition view above the slider", "it can unload / reload parts" (screenshots)
**Result:** The banner fits on one row at every width (the row may be taller). On the deployed site the preload only advanced a little each time
polling woke the function, because Vercel freezes a function after its response. The build now runs in `after()`, and the timeline moved to the
Runtime Cache so every instance sees the same plan; a stale plan keeps serving while its replacement builds, so nothing unloads any more.
The white vertical lines on the slider are the change markers (edition boundaries); the named bands appear as soon as the boundaries are known.

### 19. "Fix the position of the tag", "fixed width for the date", "zoom the timeline"
**Result:** The date has a fixed width so the edition tag stays put; the tag only appears once the page states are preloaded (that is when the
names are known). Zoom − / + above the previous / next buttons (395 to 21 days, centred on the current time), a zoom label, and an automatic fit on the
editions the first time they are known. A React hydration warning (the date is formatted in the server's timezone) is suppressed on that text.

### 20. "Can the display of the page be faster as we slide?"
**Result:** Once a page is ready the swap takes 4-20 ms with no request (instant mode). The slower cases were pages not yet ready: the `/blog` preload
died on Vercel because the function was stopped before it finished and a replacement build only saved at the end. Replacement builds now save their
progress separately and resume; polling restarts a dead build; `maxDuration` is raised to 300 s.

### 21. "All documentation up to date?" (screenshots)
**Prompt:** five screenshots; four were the Scheduling screens already in the docs, one was the time preview on the staging site.
**Result:** Audited every document against the code (broken image links, stale statements, unreferenced images). Added the time preview screenshot
and a cropped banner strip, used the content type registration screenshot, converted the retina PNGs (about 12 MB) to 1900 px JPEGs, and added
operations notes for the time preview (Runtime Cache, `maxDuration`, rate limits).

### 22. "Can we use nice content type cards with images, title and/or text when possible?" (screenshot of the card chooser)
**Result:** `cards.py` registers a card on all 21 content types with Amplience's built-in templates: summary photo (pages, heroes, feature blocks,
posts, guides, spotlights, authors, the hero slot), gallery (the three row components), photo (images) and text (FAQs, announcements, listings...).
Pointers go through links and localized values (`/image/image`, `/title/values/0/value`); the old blog post card pointed at `/title`, which
stopped working when titles became localized. Pages got an optional **cover image** so their card has a picture whatever component comes first.
Every card was rendered from a real item to check it (`docs/images/content-type-cards.jpg`).

### 23. "Why does it take forever to load the progress and there is no timeline with the editions above the slider?" (screenshot)
**Result:** The deployed preload did finish (about 45 s cold) but showed the worst picture meanwhile: the fill was missing exactly where the editions
are, bands only appeared at the very end and the view fitted once on partial data. Change points are now located left to right, two at a time, so markers
and bands arrive progressively; stretches known to contain a change pulse on the track; the view refits as they are found (until you zoom); pacing is
about 6 requests/s (limit 7/s). Local cold build 23 s to 20 s.

### 24. "Warm the timeline after each deploy. This is for demo purposes and should fly"
**Result:** `GET /api/warm` (preview only, protected by `WARM_TOKEN`) registers the requests of a typical visit and builds the timeline in the background
(`after()`, `maxDuration` 300). A GitHub Action calls it when a Preview deployment is ready; the Runtime Cache is shared by all preview deployments, so staging is warm too.
Cache lifetime 4 h, rebuild after 5 min of use with the old one serving, and the page re-renders itself when a fresher timeline replaces it. Tested locally: after warming,
home, blog and French home are instantly ready on the first visit. A tooling slip worth remembering: `path` is a special variable in zsh (tied to `$PATH`).

### 25. Making the warm-up dependable
**Result:** The first workflow was invalid YAML (an unquoted `: ` inside the input description made GitHub fail the run in 0 s; fixed and validated). Vercel reports the
environment as `Preview` and a `success` status with the deployment URL, so the condition matches. A real test on staging showed the build started in the background by
the warm call had not finished minutes later (it only completed after a visit restarted it), so `/api/warm` now builds **inside its own request** and returns the outcome
(cold: 123 s, `ready: true`, 5 markers; warm: instant), which also shows up in the Action's log.

### French catalog content from BigCommerce
**Prompt:** BigCommerce categories and products are translated already, so get the right content for the locale (it works in the Catalyst project).

**Result:** The Storefront GraphQL API **ignores `Accept-Language`**; the Catalyst client selects the language with an `@shopperPreferences(locale: "fr")` directive on the operation (short code `fr`; `fr-FR` is not accepted). `gql()` now adds it for non-default locales, so product names and descriptions, categories, custom-field labels and facet values come back translated (151 products, 19 categories and 1,231 custom fields have French in BigCommerce). BigCommerce also translates URL paths and a product path only resolves in its own language, so the shared English slugs (D9) are kept by restoring each `path` from the default-locale catalog by entity id, resolving a product page through its English path and then reading the translated content by id. PDP key specs match on the English field name (`key`), the mega menu matches tiles by path, and cart links use the restored path. Verified on 23 French pages (no translated-path links), filters, the cart flow and English pages unchanged. Ported identically to the ContentStack and Amplience storefronts.
