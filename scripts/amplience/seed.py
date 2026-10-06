"""Seed the Commerce B2B sample content (EN + FR) into Amplience, upload its images and publish everything.

    python3 scripts/amplience/seed.py            # upload assets, create/update items, publish
    python3 scripts/amplience/seed.py --no-publish

Idempotent: assets are upserted by name, items by label. All content is fictional sample text.
"""
import json
import re
import sys
import textwrap
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from assets import upload  # noqa: E402
from data.content import AUTHORS, POSTS  # noqa: E402
from data.content_extra import ANNOUNCEMENTS, FAQS, GUIDES, HOME, NAV, P, SPOTLIGHTS  # noqa: E402
from data.content_fr import (  # noqa: E402
    ANNOUNCEMENTS_FR, AUTHOR_BIOS_FR, FAQS_FR, GUIDES_FR, HEROES_FR, HOME_FR, NAV_FR, PAGES_FR,
    SPOTLIGHT_SUMMARY_FR, SPOTLIGHTS_FR, THEME_KEYWORDS_FR,
)
from data.content_fr_posts import POSTS_FR  # noqa: E402
from lib import L, SLOTS_REPO, ROOT, Items, clink, ilink  # noqa: E402

IMG = Path(__file__).parent / "images"
CACHE = Path(__file__).parent / ".assets-cache.json"
items = Items()
assets = json.loads(CACHE.read_text()) if CACHE.exists() else {}


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def md_from_html(html):
    """The sample copy only uses <p> and <a>; turn it into markdown."""
    s = re.sub(r"<a href=\"([^\"]+)\">(.*?)</a>", r"[\2](\1)", html)
    s = s.replace("</p>", "\n\n")
    return re.sub(r"<[^>]+>", "", s).strip()


def shorten(s, n=180):
    return textwrap.shorten(s, n, placeholder="…")


# ---------------------------------------------------------------- images
def image(name, file, alt_en, alt_fr=None):
    """Upload `file` as asset `name` (once) and create the `image` wrapper item. Returns the item id."""
    if name not in assets:
        path = IMG / file
        if not path.exists():
            raise SystemExit(f"missing image {path}")
        a = upload(path, name)
        assets[name] = {"assetId": a["assetId"], "name": a["name"]}
        CACHE.write_text(json.dumps(assets, indent=1))
        print(f"  uploaded {name}")
    return items.upsert("image", f"Image: {name}", {"image": ilink(assets[name]), "altText": L(alt_en, alt_fr or alt_en)})


# ---------------------------------------------------------------- content
def main():
    publish = "--no-publish" not in sys.argv

    # ---- authors
    print("== authors")
    author = []
    for a, bio_fr in zip(AUTHORS, AUTHOR_BIOS_FR):
        slug = slugify(a["name"])
        img = image(f"b2b-author-{slug}", f"author-{slug}.png", f"Portrait of {a['name']}", f"Portrait de {a['name']}")
        author.append(items.upsert("author", f"Author: {a['name']}", {"name": a["name"], "avatar": clink("image", img), "bio": L(a["bio"], bio_fr)}))

    # ---- blog posts
    print("== blog posts")
    flat = [(ai, pi, p) for ai, ps in enumerate(POSTS) for pi, p in enumerate(ps)]
    flat_fr = [p for ps in POSTS_FR for p in ps]
    start = date(2026, 1, 12)
    post_ids = []
    for (ai, pi, en), fr in zip(flat, flat_fr):
        (title, intro, s1, s2, tk), (title_f, intro_f, s1f, s2f, tkf) = en, fr
        slug = slugify(title)
        img = image(f"b2b-post-{slug[:60]}", f"post-photo-{slug[:60]}.jpg", title, title_f)

        def md(intro, s1, s2, tk, tk_heading):
            bullets = "\n".join(f"- {t}" for t in tk)
            return f"{intro}\n\n## {s1[0]}\n\n{s1[1]}\n\n## {s2[0]}\n\n{s2[1]}\n\n## {tk_heading}\n\n{bullets}\n"

        text = items.upsert("text", f"Post text: {slug[:70]}", {
            "text": L(md(intro, s1, s2, tk, "Key takeaways"), md(intro_f, s1f, s2f, tkf, "À retenir"))})
        words = len(intro.split()) + len(s1[1].split()) + len(s2[1].split())
        post_ids.append(items.upsert("blogpost", f"Post: {slug[:80]}", {
            "_meta": {"deliveryKey": f"blog/{slug}"},
            "account": "Commerce B2B",
            "title": L(title, title_f),
            "authors": [clink("author", author[ai])],
            "date": (start + timedelta(days=7 * (pi * 6 + ai))).isoformat(),
            "category": "Various",
            "description": L(shorten(intro), shorten(intro_f)),
            "image": clink("image", img),
            "tags": ["b2b commerce", AUTHORS[ai]["theme"].lower()],
            "readTime": max(3, round(words * 3 / 200)),
            "content": [clink("text", text)],
        }))
    print(f"  {len(post_ids)} posts")

    # ---- FAQs
    print("== faqs")
    faq = {}
    for i, ((topic, q, paras, featured), (q_f, paras_f)) in enumerate(zip(FAQS, FAQS_FR)):
        faq[q] = items.upsert("faq", f"FAQ: {q[:80]}", {
            "question": L(q, q_f), "answer": L("\n\n".join(paras), "\n\n".join(paras_f)),
            "topic": topic, "sortOrder": i, "featured": featured})

    # ---- buying guides
    print("== buying guides")
    guide = []
    for gi, (g, gf) in enumerate(zip(GUIDES, GUIDES_FR)):
        slug = slugify(g["title"])
        img = image(f"b2b-guide-{slug[:45]}", f"guide-photo-{slug[:45]}.jpg", g["title"], gf["title"])
        guide.append(items.upsert("buying-guide", f"Guide: {slug[:80]}", {
            "_meta": {"deliveryKey": f"guides/{slug}"},
            "title": L(g["title"], gf["title"]), "summary": L(g["summary"], gf["summary"]),
            "image": clink("image", img), "sortOrder": gi, "audience": g["audience"], "readMinutes": g["minutes"],
            "steps": [{"title": L(t, tf), "body": L(b, bf), **({"proTip": L(tip, tipf)} if tip else {})}
                      for (t, b, tip), (tf, bf, tipf) in zip(g["steps"], gf["steps"])],
            "checklist": [L(c, cf) for c, cf in zip(g["checklist"], gf["checklist"])],
            "recommendedProducts": [{"bcProductId": P[k][0], "sku": P[k][1]} for k in g["products"]],
            "relatedFaqs": [clink("faq", faq[q]) for q in g["faqs"]],
            "author": clink("author", author[g["author"]]),
        }))

    # ---- product spotlights
    print("== product spotlights")
    spot = []
    for (key, title, tagline, badge, feats, uses, _pairs, featured), (tag_f, feats_f, uses_f) in zip(SPOTLIGHTS, SPOTLIGHTS_FR):
        pid, sku = P[key]
        img = image(f"b2b-spotlight-{key}", f"spotlight-photo-{key}.png", title)
        check = "Check the specification against the vehicle's original battery before ordering, and see our buying guide for a step-by-step fitment check."
        spot.append(items.upsert("product-spotlight", f"Spotlight: {title[:80]}", {
            "title": L(title, title), "bcProductId": pid, "bcSku": sku, "tagline": L(tagline, tag_f),
            "summary": L(f"{tagline}.\n\n{check}", f"{tag_f}.\n\n{SPOTLIGHT_SUMMARY_FR}"),
            "keyFeatures": [L(f, ff) for f, ff in zip(feats, feats_f)],
            "useCases": [{"title": L(u, uf), "description": L(d, df)} for (u, d), (uf, df) in zip(uses, uses_f)],
            "badge": badge, "image": clink("image", img), "featured": featured}))

    # ---- announcements
    print("== announcements")
    ann = []
    for a, (_t, msg_f, cta_f) in zip(ANNOUNCEMENTS, ANNOUNCEMENTS_FR):
        ann.append(items.upsert("announcement-bar", f"Announcement: {a['title']}", {
            "message": L(a["message"], msg_f), "cta": {"label": L(a["cta"][0], cta_f), "href": a["cta"][1]},
            "style": a["style"], "audience": a["audience"]}))

    # ---- navigation
    print("== navigation")
    items.upsert("site-navigation", "Site navigation", {
        "_meta": {"deliveryKey": "site/navigation"},
        "headerLinks": [{"label": L(l, lf), "href": h, "highlight": False}
                        for (l, h), (lf, _) in zip(NAV["header"], NAV_FR["header"])],
        "footerColumns": [{"heading": L(h, hf), "links": [{"label": L(l, lf), "href": u} for (l, u), (lf, _) in zip(ls, lsf)]}
                          for (h, ls), (hf, lsf) in zip(NAV["footer"], NAV_FR["footer"])],
        "contact": {"salesEmail": NAV["contact"][0], "supportPhone": NAV["contact"][1],
                    "openingHours": L(NAV["contact"][2], NAV_FR["hours"])},
        "legalText": L(NAV["legal"], NAV_FR["legal"]),
        "announcements": [clink("announcement-bar", a) for a in ann],
    })

    # ---- heroes
    print("== heroes")
    hero_def = {  # key: (title, description, (cta label, href), photo)
        "home": (*[HOME["title"], HOME["description"], ("Browse buying guides", "/guides")], "hero-home-photo.jpg"),
        "faq": ("Frequently asked questions", "Quick answers for trade buyers on ordering, pricing and credit, delivery, accounts and fitment.",
                ("Browse buying guides", "/guides"), "hero-faq-photo.jpg"),
        "guides": ("Buying guides", "Practical, step-by-step checklists for matching the right battery to the job, for workshops, fleets and leisure buyers.",
                   ("Read the FAQ", "/faq"), "hero-guides-photo.jpg"),
        "blog": ("The B2B Commerce Blog", "Practical guidance on pricing, ordering, integrations, payments, sales and headless storefronts for B2B commerce teams.",
                 ("Browse articles", "/blog"), "blog-hero-photo.jpg"),
    }
    hero, hero_img = {}, {}
    for key, (title, desc, (cta_l, cta_h), photo) in hero_def.items():
        t_f, d_f, c_f, _h = HEROES_FR[key]
        img = image(f"b2b-hero-{key}", photo, title, t_f)
        hero_img[key] = img
        body = {"title": L(title, t_f), "description": L(desc, d_f), "image": clink("image", img),
                "cta": {"label": L(cta_l, c_f), "href": cta_h}, "variant": "default"}
        if key == "home":
            body["variant"] = "home"
            body["secondImage"] = clink("image", image("b2b-hero-home-second", "home-second-photo.jpg", title, t_f))
        hero[key] = items.upsert("hero-banner", f"Hero: {key}", body)

    # ---- hero slot (schedulable): holds the default home hero; see schedule.py for a scheduled alternative
    home_slot = items.upsert("hero-slot", "Home hero slot", {
        "_meta": {"deliveryKey": "slots/home-hero"}, "campaign": "Standard hero",
        "slotContent": [clink("hero-banner", hero["home"])]}, repo=SLOTS_REPO)

    # ---- components and pages
    print("== pages")
    blocks = []
    for i, ((t, copy, layout, _), (t_f, copy_f)) in enumerate(zip(HOME["blocks"], HOME_FR["blocks"])):
        img = image(f"b2b-home-block-{i}", f"home-block-photo-{i}.jpg", t, t_f)
        blocks.append(items.upsert("feature-block", f"Feature: {t}", {
            "title": L(t, t_f), "copy": L(md_from_html(copy), md_from_html(copy_f)),
            "image": clink("image", img), "layout": layout}))

    intro = items.upsert("text", "Home intro", {"text": L(md_from_html(HOME["rich_text"]), md_from_html(HOME_FR["rich_text"]).replace("/fr/", "/"))})
    tiles = items.upsert("category-tiles", "Home category tiles", {"title": L("Shop by category", "Acheter par catégorie")})
    featured_spots = [s for s, d in zip(spot, SPOTLIGHTS) if d[7]][:3]
    row_spots = items.upsert("spotlight-row", "Home trade favourites", {
        "title": L("Trade favourites", "Les favoris des pros"), "spotlights": [clink("product-spotlight", s) for s in featured_spots]})
    row_guides = items.upsert("guide-row", "Home guides row", {
        "title": L("From the buying guides", "Dans les guides d'achat"), "linkLabel": L("Buying guides", "Guides d'achat"),
        "guides": [clink("buying-guide", g) for g in guide[:3]]})

    def page(key, label, title, title_f, desc, desc_f, comps):
        return items.upsert("page", label, {
            "_meta": {"deliveryKey": key}, "title": L(title, title_f), "description": L(desc, desc_f),
            "image": clink("image", hero_img[key]), "components": comps})  # cover = the page hero's image

    page("home", "Page: home", HOME["title"], HOME["title"], HOME["description"], HOME_FR["description"],
         [clink("hero-slot", home_slot), clink("text", intro), clink("category-tiles", tiles)]
         + [clink("feature-block", b) for b in blocks]
         + [clink("spotlight-row", row_spots), clink("guide-row", row_guides)])

    page("faq", "Page: FAQ", "FAQ", PAGES_FR["/faq"][0], hero_def["faq"][1], PAGES_FR["/faq"][1],
         [clink("hero-banner", hero["faq"]),
          clink("faq-section", items.upsert("faq-section", "FAQ section", {"faqs": [clink("faq", f) for f in faq.values()]}))])

    page("guides", "Page: guides", "Buying Guides", PAGES_FR["/guides"][0], hero_def["guides"][1], PAGES_FR["/guides"][1],
         [clink("hero-banner", hero["guides"]),
          clink("guide-listing", items.upsert("guide-listing", "Guide listing", {"title": L("Buying guides", "Guides d'achat")}))])

    latest = sorted(range(len(flat)), key=lambda i: -(flat[i][1] * 6 + flat[i][0]))[:3]
    page("blog", "Page: blog", "Blog", "Blog", hero_def["blog"][1], HEROES_FR["blog"][1],
         [clink("hero-banner", hero["blog"]),
          clink("post-grid", items.upsert("post-grid", "Blog latest articles", {
              "title": L("Latest articles", "Derniers articles"), "posts": [clink("blogpost", post_ids[i]) for i in latest]})),
          clink("post-listing", items.upsert("post-listing", "Blog listing", {
              "title": L("All articles", "Tous les articles"),
              "searchPlaceholder": L("Search articles", "Rechercher des articles"),
              "searchButtonLabel": L("Search", "Rechercher")}))])

    print(f"== {len(items.order)} items created/updated")
    if publish:
        print("== publishing (dependency order)")
        items.publish_all()
    print("done")


if __name__ == "__main__":
    main()
