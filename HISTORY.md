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
