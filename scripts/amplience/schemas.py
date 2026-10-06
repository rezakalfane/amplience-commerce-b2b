"""JSON schemas for the Commerce B2B content model (everything under https://content.commerce.com/).

Text fields are field-level localizable (values: [{locale, value}]); the storefront asks the Delivery API for
`locale=fr-FR,en-US`. Links, numbers, enums and booleans are shared by all locales.
"""
import json

NS = "https://content.commerce.com/"
CORE = "http://bigcontent.io/cms/schema/v1/core"
SCHEMA = "http://json-schema.org/draft-07/schema#"
LOCALES = ["en-US", "fr-FR"]


# ---------------------------------------------------------------- building blocks
def lstr(title, desc="", markdown=False, **c):
    """Localizable string (or markdown) property."""
    value = {"title": title, "type": "string", **c}
    if markdown:
        value["format"] = "markdown"
    return {
        "title": title,
        "description": desc,
        "allOf": [{"$ref": f"{CORE}#/definitions/localized-value"}],
        "properties": {"values": {"items": {"properties": {"value": value}}}},
    }


def link(types, title, desc=""):
    """Link to one content item of the given content types (schema ids relative to NS)."""
    return {
        "title": title,
        "description": desc,
        "allOf": [
            {"$ref": f"{CORE}#/definitions/content-link"},
            {"properties": {"contentType": {"enum": [NS + t for t in types]}}},
        ],
    }


def links(types, title, desc="", min_items=0, max_items=50):
    return {
        "title": title,
        "description": desc,
        "type": "array",
        "minItems": min_items,
        "maxItems": max_items,
        "items": link(types, title)["allOf"] and {"allOf": link(types, title)["allOf"]},
    }


def cta(title="Call to action"):
    return {
        "title": title,
        "type": "object",
        "properties": {
            "label": lstr("Label", maxLength=60),
            "href": {
                "title": "Link",
                "description": "Site path without language prefix (e.g. /guides) or a full https:// URL",
                "type": "string",
                "maxLength": 300,
            },
        },
        "propertyOrder": ["label", "href"],
    }


def meta_key(desc):
    return {
        "type": "object",
        "properties": {"deliveryKey": {"type": "string", "title": "Delivery key", "description": desc}},
    }


def base(sid, title, description, props, order, required=(), extra=None):
    body = {
        "$schema": SCHEMA,
        "$id": NS + sid,
        "title": title,
        "description": description,
        "allOf": [{"$ref": f"{CORE}#/definitions/content"}],
        "type": "object",
        "properties": props,
        "propertyOrder": order,
        "required": list(required),
    }
    body.update(extra or {})
    return body


MEDIA = ["image", "video"]

# Page components (what an editor can stack in a Page)
COMPONENTS = [
    "hero-banner", "hero-slot", "feature-block", "text", "image", "video", "category-tiles",
    "spotlight-row", "guide-row", "post-grid", "post-listing", "guide-listing", "faq-section",
]

# ---------------------------------------------------------------- existing schemas (new, localizable versions)
S = {}

S["image"] = base(
    "image", "Image", "An image from the DAM with localizable alt text",
    {
        "image": {"title": "Image", "description": "Pick an image from Assets", "type": "object",
                  "anyOf": [{"$ref": f"{CORE}#/definitions/image-link"}]},
        "altText": lstr("Alt text", "Describes the image for screen readers", minLength=1, maxLength=150),
    },
    ["image", "altText"], ["image", "altText"],
)

S["video"] = base(
    "video", "Video", "A video from the DAM with a localizable title",
    {
        "video": {"title": "Video", "type": "object", "anyOf": [{"$ref": f"{CORE}#/definitions/video-link"}]},
        "videotitle": lstr("Video title", "Enter the title for the video", maxLength=80),
    },
    ["videotitle", "video"], ["videotitle", "video"],
)

S["text"] = base(
    "text", "Text", "Localizable markdown text",
    {"text": lstr("Text", "Markdown", markdown=True, minLength=1, maxLength=30000)},
    ["text"], ["text"],
)

S["author"] = base(
    "author", "Author", "An author (name, avatar and localizable bio)",
    {
        "name": {"title": "Author name", "description": "Name of the author", "type": "string", "minLength": 1, "maxLength": 100},
        "avatar": link(["image"], "Avatar", "The author's avatar"),
        "bio": lstr("Bio", "Short biography", maxLength=600),
    },
    ["name", "avatar", "bio"], ["name"],
)

S["blogpost"] = base(
    "blogpost", "Blog post", "A blog post",
    {
        "title": lstr("Title", "Used for heading and SEO title tag", minLength=1, maxLength=150),
        "date": {"title": "Creation date", "description": "Creation date (YYYY-MM-DD)", "type": "string", "minLength": 10, "maxLength": 10},
        "account": {"title": "Account", "description": "Account name", "type": "string",
                    "enum": ["Microsoft", "Colgate", "Commerce B2B"]},
        "category": {"title": "Category", "description": "Blog post category", "type": "string",
                     "enum": ["Hygienist", "Dentist", "Various"]},
        "description": lstr("Description", "Used for blog listing page and SEO description", minLength=1, maxLength=300),
        "image": link(["image"], "Image", "Used for the blog post's thumbnail and banner"),
        "_meta": meta_key("The delivery key is the URL path, e.g. blog/my-post"),
        "tags": {"title": "Tags", "description": "Blog tags", "type": "array", "minItems": 0, "maxItems": 10,
                 "items": {"type": "string", "minLength": 1, "maxLength": 100, "title": "Tag"}},
        "readTime": {"title": "Read time", "description": "Minutes to read", "type": "integer"},
        "authors": links(["author"], "Blog author", "Article author(s) - max 3", 1, 3),
        "content": links(["image", "video", "text"], "Content", "", 1, 20),
    },
    ["account", "title", "authors", "date", "category", "description", "image", "_meta", "tags", "readTime", "content"],
    ["account", "title", "authors", "date", "description", "image", "_meta", "readTime", "content"],
    extra={
        "trait:sortable": {"sortBy": [
            {"key": "default", "paths": ["/date", "/ranking"]},
            {"key": "readTime", "paths": ["/readTime", "/date", "/ranking"], "graphql:sortname": "byTime"},
        ]},
        "trait:filterable": {"filterBy": [
            {"graphql:filtername": "byCategory", "paths": ["/category"]},
            {"graphql:filtername": "byAccount", "paths": ["/account"]},
            {"graphql:filtername": "byAccountAndCategory", "paths": ["/account", "/category"]},
        ]},
    },
)

# ---------------------------------------------------------------- content types
S["hero-banner"] = base(
    "hero-banner", "Hero banner", "A page hero: headline, supporting text, image and a call to action",
    {
        "title": lstr("Title", minLength=1, maxLength=120),
        "description": lstr("Description", maxLength=400),
        "image": link(["image"], "Image", "Hero photo or artwork"),
        "secondImage": link(["image"], "Second image", "Optional second image (home variant)"),
        "cta": cta("Call to action"),
        "variant": {"title": "Variant", "type": "string", "enum": ["default", "home"], "default": "default"},
    },
    ["title", "description", "image", "secondImage", "cta", "variant"], ["title"],
)

S["feature-block"] = base(
    "feature-block", "Feature block", "An image next to a title and markdown copy",
    {
        "title": lstr("Title", minLength=1, maxLength=120),
        "copy": lstr("Copy", markdown=True, maxLength=2000),
        "image": link(["image"], "Image"),
        "layout": {"title": "Layout", "type": "string", "enum": ["image_left", "image_right"], "default": "image_left"},
    },
    ["title", "copy", "image", "layout"], ["title", "copy"],
)

S["category-tiles"] = base(
    "category-tiles", "Category tiles", "Shop-by-category tiles, read from the BigCommerce category tree",
    {"title": lstr("Title", maxLength=120)},
    ["title"], [],
)

S["faq"] = base(
    "faq", "FAQ", "A question and its answer",
    {
        "question": lstr("Question", minLength=1, maxLength=200),
        "answer": lstr("Answer", markdown=True, minLength=1, maxLength=5000),
        "topic": {"title": "Topic", "type": "string",
                  "enum": ["Ordering", "Pricing & Credit", "Delivery & Returns", "Account & Users", "Products & Fitment"]},
        "sortOrder": {"title": "Sort order", "type": "integer", "default": 0},
        "featured": {"title": "Featured", "type": "boolean", "default": False},
    },
    ["question", "answer", "topic", "sortOrder", "featured"], ["question", "answer", "topic"],
)

S["faq-section"] = base(
    "faq-section", "FAQ section", "FAQs grouped by topic (ordered by sort order)",
    {"faqs": links(["faq"], "FAQs", "", 1, 100)},
    ["faqs"], ["faqs"],
)

S["buying-guide"] = base(
    "buying-guide", "Buying guide", "A step-by-step buying guide (URL: guides/<slug>)",
    {
        "title": lstr("Title", minLength=1, maxLength=150),
        "summary": lstr("Summary", maxLength=400),
        "image": link(["image"], "Hero image"),
        "_meta": meta_key("The delivery key is the URL path, e.g. guides/how-to-choose-a-car-battery"),
        "sortOrder": {"title": "Sort order", "description": "Lower numbers first", "type": "integer", "default": 0},
        "audience": {"title": "Audience", "type": "string", "enum": ["Workshops", "Fleet managers", "Leisure & marine", "Everyone"]},
        "readMinutes": {"title": "Read time (minutes)", "type": "integer"},
        "steps": {"title": "Steps", "type": "array", "minItems": 1, "maxItems": 12, "items": {
            "type": "object",
            "properties": {
                "title": lstr("Step title", maxLength=120),
                "body": lstr("Step body", maxLength=1200),
                "proTip": lstr("Pro tip", maxLength=400),
            },
            "propertyOrder": ["title", "body", "proTip"], "required": ["title", "body"]}},
        "checklist": {"title": "Checklist", "type": "array", "maxItems": 12, "items": lstr("Checklist item", maxLength=200)},
        "recommendedProducts": {"title": "Recommended products", "description": "BigCommerce products (price and stock stay in BigCommerce)",
                                "type": "array", "maxItems": 10, "items": {
            "type": "object",
            "properties": {"bcProductId": {"title": "BigCommerce product id", "type": "integer"},
                           "sku": {"title": "SKU", "type": "string"}},
            "propertyOrder": ["bcProductId", "sku"], "required": ["bcProductId"]}},
        "relatedFaqs": links(["faq"], "Related FAQs", "", 0, 10),
        "author": link(["author"], "Author"),
    },
    ["title", "summary", "image", "_meta", "sortOrder", "audience", "readMinutes", "steps", "checklist", "recommendedProducts", "relatedFaqs", "author"],
    ["title", "summary", "_meta", "steps"],
)

S["guide-row"] = base(
    "guide-row", "Guide row", "A row of selected buying guides with a link to all guides",
    {
        "title": lstr("Title", maxLength=120),
        "linkLabel": lstr("Link label", maxLength=60),
        "guides": links(["buying-guide"], "Guides", "", 1, 6),
    },
    ["title", "linkLabel", "guides"], ["guides"],
)

S["guide-listing"] = base(
    "guide-listing", "Guide listing", "A grid of all buying guides",
    {"title": lstr("Title", maxLength=120)},
    ["title"], [],
)

S["product-spotlight"] = base(
    "product-spotlight", "Product spotlight", "Editorial layer over a BigCommerce product (keyed by product id)",
    {
        "title": lstr("Title", maxLength=150),
        "bcProductId": {"title": "BigCommerce product id", "type": "integer"},
        "bcSku": {"title": "SKU", "type": "string"},
        "tagline": lstr("Tagline", maxLength=200),
        "summary": lstr("Editorial summary", markdown=True, maxLength=1000),
        "keyFeatures": {"title": "Key features", "type": "array", "maxItems": 8, "items": lstr("Feature", maxLength=150)},
        "useCases": {"title": "Use cases", "type": "array", "maxItems": 6, "items": {
            "type": "object",
            "properties": {"title": lstr("Use case", maxLength=100), "description": lstr("Description", maxLength=300)},
            "propertyOrder": ["title", "description"]}},
        "badge": {"title": "Badge", "type": "string", "enum": ["None", "New in", "Best seller", "Trade favourite", "Heavy duty"], "default": "None"},
        "image": link(["image"], "Editorial image"),
        "featured": {"title": "Featured", "type": "boolean", "default": False},
    },
    ["title", "bcProductId", "bcSku", "tagline", "summary", "keyFeatures", "useCases", "badge", "image", "featured"],
    ["title", "bcProductId", "tagline"],
)

S["spotlight-row"] = base(
    "spotlight-row", "Spotlight row", "A row of product spotlights (product cards with editorial copy)",
    {
        "title": lstr("Title", maxLength=120),
        "spotlights": links(["product-spotlight"], "Spotlights", "", 1, 6),
    },
    ["title", "spotlights"], ["spotlights"],
)

S["post-grid"] = base(
    "post-grid", "Post grid", "A titled grid of selected blog posts",
    {"title": lstr("Title", maxLength=120), "posts": links(["blogpost"], "Posts", "", 1, 12)},
    ["title", "posts"], ["posts"],
)

S["post-listing"] = base(
    "post-listing", "Post listing", "All blog posts with search",
    {
        "title": lstr("Title", "Heading above the list", maxLength=120),
        "searchPlaceholder": lstr("Search placeholder", maxLength=80),
        "searchButtonLabel": lstr("Search button label", maxLength=40),
    },
    ["title", "searchPlaceholder", "searchButtonLabel"], [],
)

S["announcement-bar"] = base(
    "announcement-bar", "Announcement bar", "A site-wide banner shown above the header",
    {
        "message": lstr("Message", minLength=1, maxLength=200),
        "cta": cta("Call to action"),
        "style": {"title": "Style", "type": "string", "enum": ["info", "promo", "warning"], "default": "info"},
        "audience": {"title": "Audience", "type": "string", "enum": ["everyone", "logged_in", "guests"], "default": "everyone"},
    },
    ["message", "cta", "style", "audience"], ["message"],
)

S["site-navigation"] = base(
    "site-navigation", "Site navigation", "Header links, footer columns, contact details and announcements (singleton)",
    {
        "_meta": meta_key("site/navigation"),
        "headerLinks": {"title": "Header links", "type": "array", "maxItems": 8, "items": {
            "type": "object",
            "properties": {"label": lstr("Label", maxLength=40), "href": {"title": "Link", "type": "string"},
                           "highlight": {"title": "Highlight", "type": "boolean", "default": False}},
            "propertyOrder": ["label", "href", "highlight"]}},
        "footerColumns": {"title": "Footer columns", "type": "array", "maxItems": 4, "items": {
            "type": "object",
            "properties": {
                "heading": lstr("Heading", maxLength=40),
                "links": {"title": "Links", "type": "array", "maxItems": 8, "items": {
                    "type": "object",
                    "properties": {"label": lstr("Label", maxLength=60), "href": {"title": "Link", "type": "string"}},
                    "propertyOrder": ["label", "href"]}}},
            "propertyOrder": ["heading", "links"]}},
        "contact": {"title": "Contact", "type": "object", "properties": {
            "salesEmail": {"title": "Sales email", "type": "string"},
            "supportPhone": {"title": "Support phone", "type": "string"},
            "openingHours": lstr("Opening hours", maxLength=80)},
            "propertyOrder": ["salesEmail", "supportPhone", "openingHours"]},
        "legalText": lstr("Legal text", maxLength=200),
        "announcements": links(["announcement-bar"], "Announcements", "First one that matches the visitor's audience is shown", 0, 5),
    },
    ["_meta", "headerLinks", "footerColumns", "contact", "legalText", "announcements"], ["_meta"],
)

S["hero-slot"] = base(
    "hero-slot", "Hero slot", "A schedulable slot holding a hero banner (use Editions to plan which hero shows when)",
    {"slotContent": links(["hero-banner"], "Content", "The hero banner shown while this slot is live", 0, 1)},
    [], ["slotContent"],
)

S["page"] = base(
    "page", "Page", "A page: stack components in any order. The delivery key is the URL path (home, faq, guides, blog).",
    {
        "title": lstr("Title", "Used for the browser title", minLength=1, maxLength=120),
        "description": lstr("Description", "SEO description", maxLength=300),
        "_meta": meta_key("The delivery key is the URL path without language: home, faq, guides, blog, or any new path"),
        "components": links(COMPONENTS, "Components", "Stacked top to bottom", 0, 40),
    },
    ["title", "description", "_meta", "components"], ["title", "_meta", "components"],
)

SLOT_SCHEMAS = {"hero-slot"}
# Order matters only for readability; Amplience resolves $ref by content type id at validation time.
LABELS = {sid: s["title"] for sid, s in S.items()}


def body(sid):
    return json.dumps(S[sid], indent=2, ensure_ascii=False)
