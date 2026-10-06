"""Seed the scheduling example: the home hero swaps to a seasonal banner on 15 Nov 2026 and back on 5 Jan 2027.

Slots are published through Editions. This creates one event with two scheduled editions that each put a hero banner
in the `home-hero` slot. Re-running is safe: existing events with the same name are left alone.

    python3 scripts/amplience/schedule.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from assets import upload  # noqa: E402
from data.content_extra import HOME  # noqa: E402
from lib import HUB_ID, ROOT, SLOTS_REPO, FOLDER_C_B2B, EN, FR, Items, L, clink, ilink, paged, rest  # noqa: E402
from seed import CACHE, IMG, assets, image, items  # noqa: E402,F401

import json  # noqa: E402

EVENT = "Home hero: winter campaign"
EDITIONS = [
    # (name, start, end, hero label)
    ("Winter battery check", "2026-11-15T00:00:00.000Z", "2027-01-05T00:00:00.000Z", "Hero: home (winter)"),
    ("Back to the standard hero", "2027-01-05T00:00:00.000Z", "2027-12-31T00:00:00.000Z", "Hero: home"),
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
    img = image("b2b-hero-winter", "hero-guides-photo.jpg", "Winter battery check", "Contrôle des batteries avant l'hiver")
    winter = items.upsert("hero-banner", "Hero: home (winter)", {
        "title": L("Is your battery ready for winter?", "Votre batterie est-elle prête pour l'hiver ?"),
        "description": L("Book a free battery health check for your fleet or workshop before the cold sets in.",
                         "Réservez un contrôle gratuit de l'état des batteries de votre flotte ou atelier avant les premiers froids."),
        "image": clink("image", img),
        "cta": {"label": L("Read the buying guides", "Lire les guides d'achat"), "href": "/guides"},
        "variant": "default",
    })
    items.publish_all()
    hero = {"Hero: home (winter)": winter, "Hero: home": items.existing[(items_repo(), "Hero: home")]["id"]}

    if any(e["name"] == EVENT for e in paged(f"/hubs/{HUB_ID}/events", "events")):
        print("event exists, nothing to do")
        return
    event = rest("POST", f"/hubs/{HUB_ID}/events", {"name": EVENT, "comment": "Seasonal home hero (sample)",
                                                      "start": EDITIONS[0][1], "end": EDITIONS[-1][2]})
    for name, start, end, label in EDITIONS:
        ed = rest("POST", f"/events/{event['id']}/editions", {"name": name, "start": start, "end": end, "comment": f"Shows '{label}'", "activeEndDate": False})
        rest("POST", f"/editions/{ed['id']}/slots", [{"slot": slot["id"]}])
        edition_slot = next(iter(paged(f"/editions/{ed['id']}/slots", "edition-slots")))
        rest("PUT", f"/editions/{ed['id']}/slots/{edition_slot['id']}/content", {
            "label": "Home hero slot",
            "body": {"_meta": {"name": "Home hero slot", "schema": "https://content.commerce.com/hero-slot", "deliveryKey": "slots/home-hero"},
                     "slotContent": [snapshot_link(label, hero[label])]},
        })
        ed = rest("GET", f"/editions/{ed['id']}")
        rest("POST", f"/editions/{ed['id']}/schedule", {"lastModifiedDate": ed["lastModifiedDate"]})
        print(f"scheduled '{name}' for {start}")


def items_repo():
    from lib import CONTENT_REPO
    return CONTENT_REPO


if __name__ == "__main__":
    main()
