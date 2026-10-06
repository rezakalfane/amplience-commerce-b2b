"""Seed the scheduling example: the home hero changes five times between 15 Nov 2026 and 5 Jan 2027, then returns to the standard hero.

Slots are published through Editions. This creates one event with consecutive scheduled editions that each put a hero banner
in the `home-hero` slot. Re-running replaces the event, so the schedule above can be edited.

    python3 scripts/amplience/schedule.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from assets import upload  # noqa: E402
from data.content_extra import HOME  # noqa: E402
from lib import HUB_ID, ROOT, SLOTS_REPO, FOLDER_C_B2B, EN, FR, Items, L, clink, ilink, paged, rest  # noqa: E402
from seed import CACHE, IMG, assets, image, items  # noqa: E402,F401

import json  # noqa: E402

EVENT = "Home hero: winter campaign"

# Hero banners used by the schedule: label -> (EN title, FR title, EN text, FR text, cta label EN/FR, cta href, image asset name, image file)
HEROES = {
    "Hero: home (winter)": (
        "Is your battery ready for winter?", "Votre batterie est-elle prête pour l'hiver ?",
        "Book a free battery health check for your fleet or workshop before the cold sets in.",
        "Réservez un contrôle gratuit de l'état des batteries de votre flotte ou atelier avant les premiers froids.",
        ("Read the buying guides", "Lire les guides d'achat"), "/guides", "b2b-hero-winter", "hero-guides-photo.jpg"),
    "Hero: home (trade deals)": (
        "Trade deals week", "La semaine des offres professionnelles",
        "Extra savings on batteries and chargers for trade accounts, from Black Friday to Cyber Monday. Your contract prices still apply.",
        "Remises supplémentaires sur les batteries et chargeurs pour les comptes professionnels, du Black Friday au Cyber Monday. Vos prix contractuels restent applicables.",
        ("Shop all products", "Voir tous les produits"), "/products", "b2b-hero-trade-deals", "hero-faq-photo.jpg"),
    "Hero: home (holiday cut-off)": (
        "Order by 18 December for delivery before the holidays", "Commandez avant le 18 décembre pour une livraison avant les fêtes",
        "Stock your workshop before the break: in-stock batteries ordered by the cut-off arrive before Christmas.",
        "Approvisionnez votre atelier avant la pause : les batteries en stock commandées avant la date limite arrivent avant Noël.",
        ("See delivery FAQs", "Voir la FAQ livraison"), "/faq", "b2b-hero-holiday", "blog-hero-photo.jpg"),
}

# (edition name, start, end, hero label, campaign). Consecutive, so the slot always holds exactly one hero.
# `campaign` is stored in the slot content and labels the stretch on the storefront's time preview timeline.
EDITIONS = [
    ("Winter battery check", "2026-11-15T00:00:00.000Z", "2026-11-27T00:00:00.000Z", "Hero: home (winter)", "Winter battery check"),
    ("Trade deals week", "2026-11-27T00:00:00.000Z", "2026-12-01T00:00:00.000Z", "Hero: home (trade deals)", "Trade deals week"),
    ("Winter battery check (resumes)", "2026-12-01T00:00:00.000Z", "2026-12-18T00:00:00.000Z", "Hero: home (winter)", "Winter battery check"),
    ("Holiday delivery cut-off", "2026-12-18T00:00:00.000Z", "2027-01-05T00:00:00.000Z", "Hero: home (holiday cut-off)", "Holiday delivery cut-off"),
    ("Back to the standard hero", "2027-01-05T00:00:00.000Z", "2027-12-31T00:00:00.000Z", "Hero: home", "Standard hero"),
]


def snapshot_link(label, item_id):
    """Edition slots link to a snapshot of the content item (a frozen version), not to the live item."""
    snap = rest("POST", f"/hubs/{HUB_ID}/snapshots",
                {"name": label, "comment": "Scheduled home hero", "createdFrom": "content-item", "type": "USER", "contentRoot": item_id})
    link = clink("hero-banner", snap["id"])
    link["_meta"]["rootContentItemId"] = item_id
    link["_meta"]["locked"] = True
    return link


def main():
    slot = items.existing[(SLOTS_REPO, "Home hero slot")]
    hero = {"Hero: home": items.existing[(items_repo(), "Hero: home")]["id"]}
    for label, (t_en, t_fr, d_en, d_fr, (c_en, c_fr), href, asset, file) in HEROES.items():
        img = image(asset, file, t_en, t_fr)
        hero[label] = items.upsert("hero-banner", label, {
            "title": L(t_en, t_fr), "description": L(d_en, d_fr), "image": clink("image", img),
            "cta": {"label": L(c_en, c_fr), "href": href}, "variant": "default",
        })
    items.publish_all()

    # Re-running replaces the event, so the schedule above can simply be edited.
    for e in paged(f"/hubs/{HUB_ID}/events", "events"):
        if e["name"] == EVENT:
            for ed in paged(f"/events/{e['id']}/editions", "editions"):
                try:
                    rest("DELETE", f"/editions/{ed['id']}/schedule")
                except RuntimeError:
                    pass
            for attempt in range(6):  # unscheduling takes a moment to be visible
                try:
                    rest("DELETE", f"/events/{e['id']}")
                    break
                except RuntimeError:
                    if attempt == 5:
                        raise
                    time.sleep(2)
            print("replaced the existing event")
    event = rest("POST", f"/hubs/{HUB_ID}/events", {"name": EVENT, "comment": "Seasonal home hero (sample)",
                                                      "start": EDITIONS[0][1], "end": EDITIONS[-1][2]})
    for name, start, end, label, campaign in EDITIONS:
        ed = rest("POST", f"/events/{event['id']}/editions", {"name": name, "start": start, "end": end, "comment": f"Shows '{label}'", "activeEndDate": False})
        rest("POST", f"/editions/{ed['id']}/slots", [{"slot": slot["id"]}])
        edition_slot = next(iter(paged(f"/editions/{ed['id']}/slots", "edition-slots")))
        rest("PUT", f"/editions/{ed['id']}/slots/{edition_slot['id']}/content", {
            "label": "Home hero slot",
            "body": {"_meta": {"name": "Home hero slot", "schema": "https://content.commerce.com/hero-slot", "deliveryKey": "slots/home-hero"},
                     "campaign": campaign, "slotContent": [snapshot_link(label, hero[label])]},
        })
        ed = rest("GET", f"/editions/{ed['id']}")
        rest("POST", f"/editions/{ed['id']}/schedule", {"lastModifiedDate": ed["lastModifiedDate"]})
        print(f"scheduled '{name}': {start[:10]} -> {end[:10]}  ({label})")


def items_repo():
    from lib import CONTENT_REPO
    return CONTENT_REPO


if __name__ == "__main__":
    main()
