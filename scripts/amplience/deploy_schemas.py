"""Create/update the content type schemas, register content types and assign them to repositories. Idempotent.

    python3 scripts/amplience/deploy_schemas.py [--only page,hero-banner]
"""
import sys

from lib import CONTENT_REPO, HUB_ID, SLOTS_REPO, paged, rest
from schemas import LABELS, NS, S, SLOT_SCHEMAS, body

ICON = {"size": 256, "url": "https://bigcontent.io/cms/icons/ca-types-article-image.png"}


def main():
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))

    schemas = {s["schemaId"]: s for s in paged(f"/hubs/{HUB_ID}/content-type-schemas", "content-type-schemas")}
    types = {t["contentTypeUri"]: t for t in paged(f"/hubs/{HUB_ID}/content-types", "content-types")}

    for sid in S:
        if only and sid not in only:
            continue
        uri = NS + sid
        level = "SLOT" if sid in SLOT_SCHEMAS else "CONTENT_TYPE"
        text = body(sid)
        cur = schemas.get(uri)
        if cur is None:
            cur = rest("POST", f"/hubs/{HUB_ID}/content-type-schemas", {"body": text, "schemaId": uri, "validationLevel": level})
            print("created schema", sid)
        elif cur["body"].replace(" ", "").replace("\n", "") != text.replace(" ", "").replace("\n", ""):
            cur = rest("PATCH", f"/content-type-schemas/{cur['id']}", {"body": text, "version": cur["version"], "validationLevel": level})
            print("updated schema", sid, "-> v", cur["version"])
        else:
            print("unchanged schema", sid)

        ct = types.get(uri)
        if ct is None:
            ct = rest("POST", f"/hubs/{HUB_ID}/content-types",
                      {"contentTypeUri": uri, "settings": {"label": LABELS[sid], "icons": [ICON]}})
            print("  registered content type", sid)
        # Point the content type at the latest schema version.
        try:
            rest("PATCH", f"/content-types/{ct['id']}/schema", {})
        except RuntimeError as e:
            print("  (schema sync:", str(e)[:200], ")")

        repo = SLOTS_REPO if sid in SLOT_SCHEMAS else CONTENT_REPO
        try:
            rest("POST", f"/content-repositories/{repo}/content-types", {"contentTypeId": ct["id"]})
            print("  assigned to repo", repo)
        except RuntimeError as e:
            if "already" not in str(e).lower() and "409" not in str(e):
                print("  assign:", str(e)[:300])


if __name__ == "__main__":
    main()
