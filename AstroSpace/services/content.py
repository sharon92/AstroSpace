import json

import bleach
from bleach.css_sanitizer import CSSSanitizer

from AstroSpace.constants import ALLOWED_ATTRIBUTES, ALLOWED_STYLES, ALLOWED_TAGS


CSS_SANITIZER = CSSSanitizer(allowed_css_properties=ALLOWED_STYLES)


def sanitize_rich_text(value):
    if not value:
        return ""

    return bleach.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        css_sanitizer=CSS_SANITIZER,
        strip=True,
    )


def parse_meta_store(raw_meta_store, fallback="{}"):
    if not raw_meta_store:
        return fallback

    try:
        meta_store = json.loads(raw_meta_store)
    except json.JSONDecodeError:
        return fallback

    required_keys = ("constant", "variable", "comments")
    if not isinstance(meta_store, dict) or not all(key in meta_store for key in required_keys):
        return fallback

    return json.dumps({key: meta_store[key] for key in required_keys})
