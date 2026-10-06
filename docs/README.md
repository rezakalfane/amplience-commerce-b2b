# Documentation

| Document | Read it when you want to… |
|---|---|
| [architecture.md](architecture.md) | understand how Amplience, BigCommerce and Next.js fit together, production vs preview, and how a request is served |
| [amplience.md](amplience.md) | work with the hub: repositories, the content types, delivery keys, slots and scheduling, assets |
| [visualizations.md](visualizations.md) | set up and debug Preview and Real-time preview in Dynamic Content |
| [implementation.md](implementation.md) | see how each feature works (pages and components, listing, filters, product page, cart, guides…) and where the code lives |
| [bigcommerce.md](bigcommerce.md) | work with the catalog: channel, token, the GraphQL queries, facets, categories, cart |
| [i18n.md](i18n.md) | add a language or translate content: URL strategy, field-level localization, dictionaries, hreflang |
| [seeding.md](seeding.md) | create or refresh content, images, schedules and visualizations with the scripts |
| [design-system.md](design-system.md) | build UI in the "Workbench" look: tokens, type, components, imagery |
| [operations.md](operations.md) | set up environment variables, run, deploy and troubleshoot |
| [decisions.md](decisions.md) | learn why choices were made, and what was rejected |

Also see the top-level [README](../README.md) and [HISTORY](../HISTORY.md) (every request and its outcome).

## Vocabulary

- **Content item**: one piece of Amplience content (a post, an FAQ). **Content type / schema**: its structure (JSON Schema).
- **Delivery key**: the URL-like identifier of an item (`blog/my-post`); the storefront uses it as the path.
- **Page**: a content item (`page`) that stacks components and is addressed by its delivery key.
- **Component**: a content type that can be stacked in a Page (hero, feature block, spotlight row…).
- **Slot**: a schedulable container (`hero-slot`) whose content is swapped by an **Edition** at a given date.
- **Locale**: a language version. Amplience codes are `en-US` and `fr-FR`; URL prefixes are `en` (hidden) and `fr`.
- **Virtual staging**: the Amplience delivery environment that serves the latest saved content (drafts included).
- **Visualization**: a URL template that makes Dynamic Content embed the storefront next to the content form.
- **Production / Preview**: the two content modes of the storefront (CDN, published only / virtual staging, saved content).
- **PLP / PDP**: product listing page / product detail page.
