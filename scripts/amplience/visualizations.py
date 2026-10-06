"""Register the Preview and Real-time preview visualizations on the previewable content types. Idempotent.

    python3 scripts/amplience/visualizations.py https://<staging-site> http://localhost:3000

Each URL becomes two visualizations per content type ("Preview – <host>" and "Real-time preview – <host>").
Visualizations that were not created by this script are kept.
"""
import sys
from urllib.parse import urlparse

from lib import HUB_ID, paged, rest
from schemas import NS

TYPES = [
    "page", "blogpost", "buying-guide", "hero-banner", "hero-slot", "feature-block", "category-tiles", "spotlight-row",
    "guide-row", "guide-listing", "post-grid", "post-listing", "faq-section", "text", "image", "video",
]
MARK = " – "  # our labels look like "Preview – host"; used to recognise and replace them


def label(kind, site):
    return f"{kind}{MARK}{urlparse(site).netloc}"


def main():
    sites = [s.rstrip("/") for s in sys.argv[1:]]
    if not sites:
        raise SystemExit(__doc__)
    types = {t["contentTypeUri"]: t for t in paged(f"/hubs/{HUB_ID}/content-types", "content-types")}
    for name in TYPES:
        ct = types.get(NS + name)
        if not ct:
            print("skip (no content type)", name)
            continue
        settings = ct["settings"]
        keep = [v for v in settings.get("visualizations", []) if MARK not in v["label"]]
        ours = []
        for site in sites:
            base = f"{site}/preview?id={{{{content.sys.id}}}}&vse={{{{vse.domain}}}}&locales={{{{locales}}}}"
            ours.append({"label": label("Preview", site), "templatedUri": base, "default": False})
            ours.append({"label": label("Real-time preview", site), "templatedUri": base + "&realtime=true", "default": False})
        viz = ours + keep
        for v in viz:
            v["default"] = False
        viz[0]["default"] = True
        rest("PATCH", f"/content-types/{ct['id']}", {"settings": {**settings, "visualizations": viz}})
        print("visualizations set on", name)


if __name__ == "__main__":
    main()
