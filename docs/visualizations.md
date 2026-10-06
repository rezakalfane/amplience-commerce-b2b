# Preview and real-time preview (visualizations)

Amplience embeds the storefront in an iframe next to the content form. Two visualizations are registered on the content types:

| Visualization | URL template | Shows |
|---|---|---|
| **Preview** | `<site>/preview?id={{content.sys.id}}&vse={{vse.domain}}&locales={{locales}}` | the latest **saved** version, from virtual staging |
| **Real-time preview** | same, plus `&realtime=true` | the form as you type, **without saving** |

`<site>` is the staging site (`https://amplience-commerce-b2b-git-staging-rza-kalfanes-projects.vercel.app`) or
`http://localhost:3000` for local development. `scripts/amplience/visualizations.py <site>…` registers them.

## How it works

1. **`app/preview/page.tsx`** receives the content id and the virtual staging domain. It only accepts a UUID and a host that
   ends in `.staging.bigcontent.io` (or the configured host), fetches `/content/id/<id>?depth=all&format=inlined&locale=…`
   and renders the item with `renderPreview()` (`app/preview/render.tsx`).
2. **`previewable()`** (`lib/content.ts`) maps any item the same way the live site does: a Page, a blog post, a buying guide,
   or a single component (hero, feature block, spotlight row…) rendered on its own. Components are the same React components
   as the live site, so the preview is pixel-identical.
3. With **`realtime=true`**, `RealtimePreview` (client) starts `dc-visualization-sdk`: `sdk.form.get({ allowInvalid: true })`
   for the first model, `sdk.form.changed(…)` for every edit and `sdk.locale.changed(…)` when the editor switches locale.
   Each model (debounced 150 ms) goes to the **`renderModel` server action**, which returns the rendered React tree; only the
   latest response is shown. `lib/localized.ts` resolves any `{ values: [{ locale, value }] }` wrappers the form model may still
   carry, with the same English fallback as the Delivery API.
4. Opened outside Dynamic Content (no iframe host), the SDK handshake times out after 4 seconds and the page stays on the
   server-rendered saved version; the badge in the corner says so.

```
Dynamic Content form ──postMessage──► RealtimePreview ──server action──► renderPreview() ──► React tree ──► iframe
                  saved item ──► /preview?id=… ──► virtual staging ──► renderPreview() ──► HTML
```

## Previewing the whole site from Scheduling (preview applications)

Visualizations preview one item next to its form. To preview the **site** at a date or in an edition (for example to see the
scheduled home hero), Dynamic Content uses **Settings → Preview** applications. They are a hub setting that the Management
API cannot update without the hub's DAM publishing secret, so add them in the UI:

| Preview application name | Preview application URL |
|---|---|
| `Storefront staging` | `https://amplience-commerce-b2b-git-staging-rza-kalfanes-projects.vercel.app/?vse={{vse.domain}}` |
| `Storefront local` | `http://localhost:3000/?vse={{vse.domain}}` |

`vse.domain` is a virtual staging domain **frozen at the date and time (or edition) being previewed**, shaped
`<vse id>-<token>-<unix ms>.staging.bigcontent.io`. `proxy.ts` stores it in the `amp_vse` cookie (preview deployments only, valid
`*.staging.bigcontent.io` hosts only) and redirects to the clean URL; `lib/amplience.ts` then reads every item from that host,
so the whole site, including the slot's hero, shows what will be live then. In production the parameter is ignored.

### Time preview banner

While a session is pinned to a moment, every page shows a sticky **Time preview** banner (`components/time-preview-bar.tsx`):

- the date and time being previewed, and a reminder that the catalog and prices are live (only the content is time-pinned);
- a **slider** (30 days back to a year ahead, hourly steps) and a **date/time field**: moving either re-pins the session and
  re-renders the page live through `setTimePreview` (a server action that rewrites the cookie) and `router.refresh()`;
- **Now** (jump to the present) and **Exit time preview** (clears the cookie, back to the latest saved content).

You can also enter it without Dynamic Content: `…/?time=2026-12-01T10:00` (any date `Date.parse` understands). That needs
`AMPLIENCE_TIME_TOKEN`: the `<token>` part of a time-pinned domain, which Amplience does not expose through an API. Open
any preview application once from Scheduling and copy the middle part of the domain in the address bar (it does not depend on
the date). Sessions that start from Amplience reuse the token of the domain they were given. `?vse=reset` or `?time=now` clears the pin.

## Safeguards

- `/preview` returns **404 in production** (`CONTENT_ENV === "production"`) and the server action throws there.
- The staging host and content id are validated, so the route cannot be used to fetch arbitrary URLs.
- `Content-Security-Policy: frame-ancestors` allows only `https://*.amplience.net`.
- Preview deployments are read-only: they never write to Amplience.

## Using it

1. Open an item (a Page, post, guide or component) in Dynamic Content → the visualization selector → **Real-time preview**.
2. Switch the locale in the visualization toolbar to see the French values; the device selector resizes the frame.
3. For scheduled slots, open the edition's snapshot preview: slot content is resolved by Amplience before the page is rendered.

## Troubleshooting

| Symptom | Check |
|---|---|
| Blank frame / refused to connect | the site's CSP; the visualization URL must be `https` (or `http://localhost`) |
| 404 in the frame | `AMPLIENCE_DELIVERY_HOST` is unset on that deployment (production mode), or the id is not a content item id |
| Preview works, real-time does not | the URL lacks `realtime=true`; or the page is opened outside Dynamic Content |
| Linked items missing in the frame | the linked item is archived or deleted; drafts do show in virtual staging |
