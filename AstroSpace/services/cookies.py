import json

from flask import current_app, request


COOKIE_CONSENT_COOKIE_NAME = "astrospace_cookie_preferences"
THEME_COOKIE_NAME = "astrospace_theme"
VISITOR_COOKIE_NAME = "astrospace_visitor"
COMMENTER_NAME_COOKIE_NAME = "astrospace_commenter_name"
PREFERENCE_COOKIE_PREFIX = "astrospace_pref_"

COOKIE_CONSENT_MAX_AGE = 180 * 24 * 60 * 60
PREFERENCE_COOKIE_MAX_AGE = 180 * 24 * 60 * 60
VISITOR_COOKIE_MAX_AGE = 180 * 24 * 60 * 60
COMMENTER_COOKIE_MAX_AGE = 180 * 24 * 60 * 60

DEFAULT_COOKIE_CONSENT = {
    "version": 1,
    "necessary": True,
    "preferences": False,
    "community": False,
}

COOKIE_POLICY_ROWS = [
    {
        "name": COOKIE_CONSENT_COOKIE_NAME,
        "category": "Necessary",
        "duration": "180 days",
        "purpose": "Stores your cookie consent choices so we can respect them on future visits.",
    },
    {
        "name": "session",
        "category": "Necessary",
        "duration": "Session",
        "purpose": "Maintains secure sessions, CSRF protection, and authenticated access while you browse the site.",
    },
    {
        "name": f"{PREFERENCE_COOKIE_PREFIX}*",
        "category": "Preferences",
        "duration": "180 days",
        "purpose": "Remembers optional interface choices such as saved tabs and filter-panel state when you allow preference cookies.",
    },
    {
        "name": THEME_COOKIE_NAME,
        "category": "Preferences",
        "duration": "180 days",
        "purpose": "Remembers your selected light or dark theme when you allow preference cookies.",
    },
    {
        "name": COMMENTER_NAME_COOKIE_NAME,
        "category": "Preferences",
        "duration": "180 days",
        "purpose": "Remembers the display name you chose for anonymous comments when you allow preference cookies and ask us to save it.",
    },
    {
        "name": VISITOR_COOKIE_NAME,
        "category": "Community",
        "duration": "180 days",
        "purpose": "Stores a pseudonymous visitor ID that helps us count unique post views, prevent duplicate anonymous likes, and reduce comment abuse when you allow community cookies.",
    },
]


def parse_cookie_consent(raw_value):
    if not raw_value:
        return dict(DEFAULT_COOKIE_CONSENT)

    try:
        parsed = json.loads(raw_value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return dict(DEFAULT_COOKIE_CONSENT)

    consent = dict(DEFAULT_COOKIE_CONSENT)
    if isinstance(parsed, dict):
        for key in ("preferences", "community"):
            consent[key] = bool(parsed.get(key, consent[key]))
        consent["version"] = int(parsed.get("version", consent["version"]))
    return consent


def get_cookie_consent(request_like=None):
    request_like = request_like or request
    return parse_cookie_consent(request_like.cookies.get(COOKIE_CONSENT_COOKIE_NAME))


def consent_allows(category, request_like=None):
    if category == "necessary":
        return True
    return bool(get_cookie_consent(request_like).get(category, False))


def serialize_cookie_consent(consent):
    payload = dict(DEFAULT_COOKIE_CONSENT)
    payload["preferences"] = bool(consent.get("preferences"))
    payload["community"] = bool(consent.get("community"))
    payload["version"] = int(consent.get("version", DEFAULT_COOKIE_CONSENT["version"]))
    return json.dumps(payload, separators=(",", ":"))


def preference_cookie_name(key):
    safe_key = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in str(key))
    return f"{PREFERENCE_COOKIE_PREFIX}{safe_key}"


def _cookie_secure_flag():
    if current_app.config.get("SESSION_COOKIE_SECURE"):
        return True

    forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
    if forwarded_proto:
        return forwarded_proto.split(",")[0].strip().lower() == "https"

    return request.is_secure


def set_response_cookie(response, name, value, max_age, httponly=False):
    response.set_cookie(
        name,
        value,
        max_age=max_age,
        samesite="Lax",
        secure=_cookie_secure_flag(),
        httponly=httponly,
    )


def clear_response_cookie(response, name):
    response.delete_cookie(
        name,
        samesite="Lax",
        secure=_cookie_secure_flag(),
    )
