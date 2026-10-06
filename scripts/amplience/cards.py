"""Register content type cards: the thumbnails shown for each content type in Dynamic Content's content browser. Idempotent.

    python3 scripts/amplience/cards.py

Amplience's built-in card templates (gallery, summary-photo, photo, text) read the item through the virtual staging
environment and take JSON pointers into the content tree. Pointers follow content links (`/image/image` goes through
the linked `image` item to its DAM image) and localized values (`/title/values/0/value` is the first locale).
"""
from lib import HUB_ID, paged, rest
from schemas import NS

# `src` tells the template where to read the item: virtual staging, by content id, with linked content resolved.
SRC = ("%2F%2F{{vse.domain}}%2Fcms%2Fcontent%2Fquery%3FfullBodyObject%3Dtrue%26query%3D%257B%2522sys.iri%2522%253A%2522http%253A"
       "%252F%252Fcontent.cms.amplience.com%252F{{content.sys.id}}%2522%257D%26scope%3Dtree%26store%3Dstaging")
BASE = "https://bigcontent.io/cms/cards"


def card(kind, **params):
    return f"{BASE}/{kind}/index.html?" + "&".join(f"{k}={v}" for k, v in params.items()) + f"&src={SRC}"


def loc(path):
    """First (default) locale of a localized field."""
    return f"{path}/values/0/value"


def titled_photo(image="/image"):
    """Summary photo: the item's title under its (linked) image."""
    return card("summary-photo", headline=loc("/title"), image=f"{image}/image", imageAlt=loc(f"{image}/altText"))


def gallery(list_field, n=4, headline=None):
    """Gallery: the first images of a list of linked items."""
    params = {"headline": headline or loc("/title")}
    params.update({f"image{i}": f"/{list_field}/{i}/image/image" for i in range(n)})
    return card("gallery", **params)


CARDS = {
    # pages and page components
    "page": titled_photo(),
    "hero-banner": titled_photo(),
    "hero-slot": card("summary-photo", headline="/campaign", image="/slotContent/0/image/image", imageAlt=loc("/slotContent/0/image/altText")),
    "feature-block": titled_photo(),
    "category-tiles": card("text", headline=loc("/title")),
    "spotlight-row": gallery("spotlights", 3),
    "guide-row": gallery("guides", 3),
    "guide-listing": card("text", headline=loc("/title")),
    "post-grid": gallery("posts", 3),
    "post-listing": card("text", headline=loc("/title")),
    "faq-section": card("text", headline=loc("/faqs/0/question")),
    # content
    "blogpost": titled_photo(),
    "buying-guide": titled_photo(),
    "product-spotlight": titled_photo(),
    "author": card("summary-photo", headline="/name", image="/avatar/image", imageAlt=loc("/avatar/altText")),
    "faq": card("text", headline=loc("/question")),
    "announcement-bar": card("text", headline=loc("/message")),
    "site-navigation": card("text", headline=loc("/legalText")),
    # shared building blocks
    "image": card("photo", image="/image", imageAlt=loc("/altText")),
    "text": card("text", headline=loc("/text")),
    "video": card("text", headline=loc("/videotitle")),
}


def main():
    types = {t["contentTypeUri"]: t for t in paged(f"/hubs/{HUB_ID}/content-types", "content-types")}
    for name, uri in CARDS.items():
        ct = types.get(NS + name)
        if not ct:
            print("skip (no content type)", name)
            continue
        settings = {**ct["settings"], "cards": [{"templatedUri": uri}]}
        rest("PATCH", f"/content-types/{ct['id']}", {"settings": settings})
        print("card set on", name)


if __name__ == "__main__":
    main()
