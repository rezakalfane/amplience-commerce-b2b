# Operations

## Prerequisites

- Node.js 22+ and npm (the project is built and tested on Node 24).
- Python 3.12+ (standard library only) for the Amplience scripts; optional for running the site.
- An Amplience hub with Dynamic Content, a **personal access token** (for the scripts) and a BigCommerce store with a
  storefront channel and a Storefront API token.

## Environment variables

| Variable | Where | Purpose |
|---|---|---|
| `AMPLIENCE_HUB_NAME` | storefront, scripts | hub name (`commercedemo`); builds the CDN host and image URLs |
| `AMPLIENCE_DELIVERY_HOST` | storefront | **empty = production** (the hub CDN). Set to the virtual staging host to read drafts and enable `/preview` |
| `WARM_TOKEN` | storefront (Preview scope only) + GitHub secret | shared secret for `/api/warm` |
| `AMPLIENCE_TIME_TOKEN` | storefront (Preview scope only) | token inside a time-pinned staging domain, enables `?time=` ([visualizations.md](visualizations.md#time-preview-banner)) |
| `AMPLIENCE_PAT` | scripts only | personal access token (Management + GraphQL asset APIs). Never set it in Vercel |
| `AMPLIENCE_HUB_ID` | scripts only | Management API hub id |
| `BIGCOMMERCE_STORE_HASH`, `BIGCOMMERCE_CHANNEL_ID`, `BIGCOMMERCE_STOREFRONT_TOKEN` | storefront | commerce ([bigcommerce.md](bigcommerce.md)) |

`.env.example` lists them; copy it to `.env.local` (git-ignored).

## Running locally

```bash
npm install
npm run dev          # http://localhost:3000, reads virtual staging (AMPLIENCE_DELIVERY_HOST in .env.local)
npm run build && npm start
npx tsc --noEmit && npm run lint
```

`/preview?id=<content id>&vse=<staging host>` renders any item locally; use `http://localhost:3000` as a visualization
base URL to work on the storefront with the content form open ([visualizations.md](visualizations.md)).

## Deployments (Vercel project `amplience-commerce-b2b`)

| Site | URL | Branch | Reads | Purpose |
|---|---|---|---|---|
| **Production** | https://amplience-commerce-b2b.vercel.app | `main` | published content (CDN) | the live site |
| **Staging / Preview** | https://amplience-commerce-b2b-git-staging-rza-kalfanes-projects.vercel.app | `staging` (rebuilt from `main` by `.github/workflows/sync-staging.yml`; any other branch also gets a preview) | latest saved content (virtual staging) | review changes and host the visualizations |
| **Local** | http://localhost:3000 | working copy | virtual staging | development |

Vercel environment variables (set per scope with `vercel env add <name> production|preview`):

| Variable | Production | Preview |
|---|---|---|
| `AMPLIENCE_HUB_NAME` | `commercedemo` | `commercedemo` |
| `AMPLIENCE_DELIVERY_HOST` | *(not set)* | `<id>.staging.bigcontent.io` |
| `AMPLIENCE_TIME_TOKEN` | *(not set)* | the token of a time-pinned domain |
| `BIGCOMMERCE_*` | set | set |

Each deployment reports which content it reads in the `X-Content-Environment` response header:

```bash
curl -sI https://amplience-commerce-b2b.vercel.app | grep -i x-content-environment   # production
```

Pushing to `main` deploys production; pushing to `staging` (or opening a PR) deploys a preview. Preview deployments are public
(no Vercel Authentication) because Amplience loads them in an iframe from `app.amplience.net`.

### Going live

1. Edit in Dynamic Content; check the **Preview** and **Real-time preview** visualizations (they read virtual staging).
2. **Publish** the item (and its linked items). Production serves it within about a minute (`revalidate: 60`).
3. For timed changes, put slots in an **Edition** ([amplience.md](amplience.md#scheduling-with-slots)).

### Renewing the BigCommerce Storefront token

The token expires periodically (90 days by default). Create a new one for each origin you serve
(`POST /v3/storefront/api-token` with `channel_id`, `expires_at` and a single `allowed_cors_origins` entry), update
`BIGCOMMERCE_STOREFRONT_TOKEN` in Vercel (both scopes), and redeploy. A stale token shows up as empty product sections and
`[bigcommerce] … failed` messages in the server log.

### Time preview operations

- **Warm-up after each deploy.** Building the timeline takes 1-2 minutes (nine requests per probe), so it is done before anyone asks: the GitHub Action
  `.github/workflows/warm-timeline.yml` runs when Vercel reports a **Preview** deployment ready and calls `GET /api/warm` (header `x-warm-token`, secret `WARM_TOKEN`
  in both GitHub and Vercel's Preview scope). The route registers the requests of a typical visit (`warmRequests()` in `lib/content.ts`: navigation, home, FAQ, guides, blog,
  the post and guide lists, plus French navigation and home) and **builds inside that request** (up to `maxDuration`, 300 s), so the Action's log shows the real outcome
  (`{"ready":true,"markers":5,"seconds":123,...}`; a cold build takes about two minutes, a fresh timeline answers at once). Work left running after a response is not dependable on serverless. The timeline lives in the project's Runtime Cache, which all Preview deployments
  share, so warming the new deployment also warms the staging site. The cache entry lives 4 hours; after 5 minutes of use a rebuild starts in the background and the
  page re-renders itself when the fresher timeline replaces the old one. Run it by hand: `curl -H "x-warm-token: $WARM_TOKEN" https://<preview-url>/api/warm`, or
  *Actions → Warm the time travel timeline → Run workflow*. The route is a 404 in production and without the token.
- The preload runs in the background after a response (`after()`), so `app/[locale]/layout.tsx` sets `maxDuration = 300`. A heavy page (the blog) needs about a minute the first time.
- Its state lives in the **Runtime Cache** (Observability → Runtime Cache shows it; keys start with `<staging id>:<token>`). A plan is rebuilt after 5 minutes of use (or when a page brings queries it does not cover) and entries
  expire after 4 hours; a stale plan keeps serving until its replacement completes.
- Virtual staging allows 7 requests/s (350/min) for everything on that environment; the preload uses about 6/s at most and backs off on `429`. If other tools hammer staging, the preload slows down but resumes.
- Schedules are in the hub: `python3 scripts/amplience/schedule.py` replaces the event, then the timeline refreshes itself within minutes.

## Production readiness checklist

- [x] Production and Preview deployments with separate content environments, reported by `X-Content-Environment`.
- [x] Visualizations (preview and real-time) registered on the content types.
- [ ] Preview applications added in the hub (Settings → Preview) for Scheduling and Edition previews ([visualizations.md](visualizations.md#previewing-the-whole-site-from-scheduling-preview-applications)).
- [ ] Replace all fictional sample content (authors, article text, FAQ policies, promotions, contact details).
- [ ] Add a **publish webhook** (Amplience → a Next.js route that calls `revalidateTag`) and cache Amplience reads with tags for instant updates.
- [ ] Decide the B2B account story: customer login, company price lists, quotes ([bigcommerce.md](bigcommerce.md)).
- [ ] `sitemap.xml` (the Hierarchy / Filter API can list every delivery key), `robots.txt`, canonical host, analytics, error monitoring.
- [ ] Review the cookie notice requirements for the cart cookie (`bc_cart_id`, strictly necessary).
- [ ] Run the checks (tsc, lint, build) and a manual pass on EN and FR: home, listing, product, cart, blog, guides, FAQ.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Whole site 404s on Vercel | project framework preset is "Other" | set Framework Preset to Next.js and redeploy |
| Pages render without images | the Amplience asset is not published, or the loader is bypassed | publish the asset; keep `images.loaderFile` in `next.config.ts` |
| A Page 404s | no published Page with that delivery key | check the key in the item's *Delivery keys* and that it is published |
| Empty hero on the home page | the hero slot has no published content | publish the slot (or its edition) |
| Content change not visible in production | not published, or within the 60 s cache | publish; wait a minute |
| Content change not visible in the preview site | the site is reading the CDN, not virtual staging | check `X-Content-Environment` and `AMPLIENCE_DELIVERY_HOST` |
| French page shows English text | the field has no `fr-FR` value (fallback) or a UI string is missing | add the value / the string |
| Empty product sections, `[bigcommerce] … failed` in the log | expired/wrong Storefront token, wrong channel host, origin mismatch | see "Renewing the token" |
| Product page 404 | the BigCommerce path is not on the channel, or the product is not visible | check the product's channel assignment and visibility |
| Preview frame refused / 404 | see [visualizations.md](visualizations.md#troubleshooting) | |
| `Cannot find module` after moving files | stale `.next` | stop the server, delete `.next`, restart |

## Logs and diagnostics

- Server logs include `[bigcommerce] … failed: <message>` and `[cart] … failed` lines.
- Reproduce any content read: `curl "https://commercedemo.cdn.content.amplience.net/content/key/home?depth=all&format=inlined&locale=fr-FR,en-US"`.
- Reproduce a list: `POST /content/filter` with `{"filterBy":[{"path":"/_meta/schema","value":"https://content.commerce.com/buying-guide"}],"page":{"size":12}}`.
- `curl -s -X POST https://store-<hash>-<channel>.mybigcommerce.com/graphql -H "Authorization: Bearer $TOKEN" …`
  reproduces any BigCommerce GraphQL call.

## Known limitations

- No buyer sign-in, per-company pricing, quotes or order history (B2B Edition is not yet integrated).
- Product, category and custom-field text is translated only where BigCommerce has Store Translations (French, plus any other locale added the same way).
- Production reads are cached for 60 seconds; there is no webhook-driven revalidation yet.
- The Filter API returns 12 items per request, so listings of hundreds of items need pagination in the UI.
- Search on the blog is a simple in-memory text match over all posts.
- The pre-existing demo items of the five shared schemas remain in the hub and may no longer validate.
