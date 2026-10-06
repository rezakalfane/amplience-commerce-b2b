"""Shared helpers for the Amplience seeding scripts (stdlib only).

Credentials come from ../../.env.local (AMPLIENCE_PAT, AMPLIENCE_HUB_ID, AMPLIENCE_HUB_NAME).
"""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CM = "https://api.amplience.net/v2/content"
GQL = "https://api.amplience.net/graphql"

# Ids discovered in the hub (see docs/amplience.md).
CONTENT_REPO = "691214f6ae0d392382e85b12"          # "content"
SLOTS_REPO = "691214fa066ec621d02d804a"            # "slots"
FOLDER_C_B2B = "6ac4c880eb33af28ccbe9e7a"          # Content > C > Commerce B2B
ASSET_REPO = "QXNzZXRSZXBvc2l0b3J5OjlmZDE2N2U5LWU1NTktNDM4MS05NjNmLTZmZDc4ODRlOTk2Yw=="  # "Assets" (GraphQL global id)
ASSET_FOLDER_B2B = "QXNzZXRGb2xkZXI6NWZiZmE1ZmItY2MxNS00OTA0LWI2NmItMGU3NGI2YzlmNDI3"  # Assets > C > Commerce B2B


def _env():
    env = dict(os.environ)
    p = ROOT / ".env.local"
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip().strip('"'))
    return env


ENV = _env()
PAT = ENV["AMPLIENCE_PAT"]
HUB_ID = ENV["AMPLIENCE_HUB_ID"]
HUB_NAME = ENV["AMPLIENCE_HUB_NAME"]


def call(method, url, body=None, headers=None, raw=None, retries=4):
    """HTTP call returning parsed JSON (or None for empty bodies). Retries 429/5xx."""
    h = {"Authorization": f"Bearer {PAT}", **(headers or {})}
    data = raw
    if body is not None:
        data = json.dumps(body).encode()
        h.setdefault("Content-Type", "application/json")
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                txt = r.read().decode()
                return json.loads(txt) if txt.strip() else None
        except urllib.error.HTTPError as e:
            txt = e.read().decode()
            if e.code in (429, 500, 502, 503) and attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise RuntimeError(f"{method} {url} -> {e.code}: {txt[:1500]}") from None


def rest(method, path, body=None, **kw):
    return call(method, path if path.startswith("http") else f"{CM}{path}", body, **kw)


def gql(query, variables=None):
    res = call("POST", GQL, {"query": query, "variables": variables or {}})
    if res.get("errors"):
        raise RuntimeError(json.dumps(res["errors"])[:1500])
    return res["data"]


def paged(path, embedded_key, size=100):
    """Iterate all pages of a HAL collection."""
    page = 0
    while True:
        sep = "&" if "?" in path else "?"
        res = rest("GET", f"{path}{sep}page={page}&size={size}")
        items = (res.get("_embedded") or {}).get(embedded_key, [])
        yield from items
        if page + 1 >= res["page"]["totalPages"]:
            return
        page += 1


# ---------------------------------------------------------------- content items
from schemas import NS  # noqa: E402

LINK = "http://bigcontent.io/cms/schema/v1/core#/definitions/content-link"
IMAGE_LINK = "http://bigcontent.io/cms/schema/v1/core#/definitions/image-link"
EN, FR = "en-US", "fr-FR"


def L(en, fr=None):
    """Localized value: {'values': [{'locale', 'value'}]}."""
    vals = [{"locale": EN, "value": en}]
    if fr is not None:
        vals.append({"locale": FR, "value": fr})
    return {"_meta": {"schema": "http://bigcontent.io/cms/schema/v1/core#/definitions/localized-value"}, "values": vals}


def clink(ctype, item_id):
    return {"_meta": {"schema": LINK}, "contentType": NS + ctype, "id": item_id}


def ilink(asset):
    return {"_meta": {"schema": IMAGE_LINK}, "id": asset["assetId"], "name": asset["name"],
            "endpoint": HUB_NAME, "defaultHost": "cdn.media.amplience.net"}


class Items:
    """Upsert content items by label, remembering creation order for publishing."""

    def __init__(self):
        self.existing = {}
        for repo, folder in ((CONTENT_REPO, FOLDER_C_B2B), (SLOTS_REPO, None)):
            q = f"?folderId={folder}&status=ACTIVE" if folder else "?status=ACTIVE"
            for it in paged(f"/content-repositories/{repo}/content-items{q}", "content-items"):
                self.existing[(repo, it["label"])] = it
        self.order = []

    def upsert(self, ctype, label, body, repo=CONTENT_REPO):
        body = {"_meta": {"name": label, **body.pop("_meta", {}), "schema": NS + ctype}, **body}
        cur = self.existing.get((repo, label))
        if cur is None:
            payload = {"label": label, "body": body}
            if repo == CONTENT_REPO:
                payload["folderId"] = FOLDER_C_B2B
            cur = rest("POST", f"/content-repositories/{repo}/content-items", payload)
        else:
            cur = rest("PATCH", f"/content-items/{cur['id']}", {"label": label, "body": body, "version": cur["version"]})
        self.existing[(repo, label)] = cur
        if cur["id"] not in [i for i, _ in self.order]:
            self.order.append((cur["id"], label))
        return cur["id"]

    def publish_all(self):
        for iid, label in self.order:
            it = rest("GET", f"/content-items/{iid}")
            if it.get("lastPublishedVersion") == it["version"]:
                continue
            try:
                rest("POST", f"/content-items/{iid}/publish", {})
            except RuntimeError as e:
                print("  publish failed:", label, str(e)[:300])
