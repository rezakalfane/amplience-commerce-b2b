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
