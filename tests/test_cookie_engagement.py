import json
from datetime import datetime

from AstroSpace.services.cookies import COOKIE_CONSENT_COOKIE_NAME, parse_cookie_consent
from AstroSpace.services.engagement import CommentRateLimitError, VisitorIdentity, build_visitor_identity


def test_parse_cookie_consent_defaults_to_necessary_only():
    consent = parse_cookie_consent(None)

    assert consent == {
        "version": 1,
        "necessary": True,
        "preferences": False,
        "community": False,
    }


def test_build_visitor_identity_uses_network_fingerprint_without_community_cookie(app):
    with app.test_request_context(
        "/image/7/test",
        headers={"User-Agent": "Firefox/123.0", "X-Forwarded-For": "203.0.113.10"},
    ):
        identity = build_visitor_identity()

    assert identity.visitor_source == "network"
    assert identity.new_visitor_cookie is None
    assert identity.visitor_cookie_hash is None
    assert identity.visitor_hash
    assert identity.ip_hash
    assert identity.user_agent_hash


def test_build_visitor_identity_generates_cookie_when_community_consent_is_enabled(app):
    consent_cookie = json.dumps({"version": 1, "preferences": False, "community": True})

    with app.test_request_context(
        "/image/7/test",
        headers={
            "User-Agent": "Firefox/123.0",
            "X-Forwarded-For": "203.0.113.10",
        },
        environ_overrides={
            "HTTP_COOKIE": f"{COOKIE_CONSENT_COOKIE_NAME}={consent_cookie}",
        },
    ):
        identity = build_visitor_identity()

    assert identity.visitor_source == "cookie"
    assert identity.new_visitor_cookie
    assert identity.visitor_cookie_hash == identity.visitor_hash


def test_like_endpoint_returns_counts_and_sets_visitor_cookie(app, monkeypatch):
    from AstroSpace import blog

    monkeypatch.setattr(blog, "get_image_by_id", lambda image_id: {"id": image_id, "title": "Soul Nebula"})
    monkeypatch.setattr(
        blog,
        "build_visitor_identity",
        lambda: VisitorIdentity(
            visitor_hash="visitor-hash",
            visitor_source="cookie",
            ip_hash="ip-hash",
            user_agent_hash="ua-hash",
            visitor_cookie_hash="cookie-hash",
            visitor_cookie_value="visitor-token",
            new_visitor_cookie="visitor-token",
        ),
    )
    monkeypatch.setattr(blog, "register_image_like", lambda image_id, visitor_identity: True)
    monkeypatch.setattr(
        blog,
        "fetch_image_engagement_state",
        lambda image_id, visitor_identity, include_comments=False: {
            "liked": True,
            "like_count": 4,
            "view_count": 0,
            "comment_count": 0,
            "comments": [],
        },
    )

    with app.test_request_context("/image/7/like", method="POST"):
        response = blog.like_image_endpoint(7)

    assert response.status_code == 200
    assert response.get_json() == {
        "message": "Thanks for starring this post.",
        "liked": True,
        "like_count": 4,
    }
    assert "astrospace_visitor=visitor-token" in response.headers.get("Set-Cookie", "")


def test_like_endpoint_can_remove_star_and_keep_visitor_cookie(app, monkeypatch):
    from AstroSpace import blog

    monkeypatch.setattr(blog, "get_image_by_id", lambda image_id: {"id": image_id, "title": "Soul Nebula"})
    monkeypatch.setattr(
        blog,
        "build_visitor_identity",
        lambda: VisitorIdentity(
            visitor_hash="visitor-hash",
            visitor_source="cookie",
            ip_hash="ip-hash",
            user_agent_hash="ua-hash",
            visitor_cookie_hash="cookie-hash",
            visitor_cookie_value="visitor-token",
            new_visitor_cookie="visitor-token",
        ),
    )
    monkeypatch.setattr(blog, "register_image_like", lambda image_id, visitor_identity: False)
    monkeypatch.setattr(
        blog,
        "fetch_image_engagement_state",
        lambda image_id, visitor_identity, include_comments=False: {
            "liked": False,
            "like_count": 3,
            "view_count": 0,
            "comment_count": 0,
            "comments": [],
        },
    )

    with app.test_request_context("/image/7/like", method="POST"):
        response = blog.like_image_endpoint(7)

    assert response.status_code == 200
    assert response.get_json() == {
        "message": "Star removed.",
        "liked": False,
        "like_count": 3,
    }
    assert "astrospace_visitor=visitor-token" in response.headers.get("Set-Cookie", "")


def test_comment_endpoint_sets_commenter_cookie_when_preferences_are_enabled(app, monkeypatch):
    from AstroSpace import blog

    consent_cookie = json.dumps({"version": 1, "preferences": True, "community": False})

    monkeypatch.setattr(blog, "get_image_by_id", lambda image_id: {"id": image_id, "title": "Soul Nebula"})
    monkeypatch.setattr(
        blog,
        "build_visitor_identity",
        lambda: VisitorIdentity(
            visitor_hash="visitor-hash",
            visitor_source="network",
            ip_hash="ip-hash",
            user_agent_hash="ua-hash",
            visitor_cookie_hash=None,
            visitor_cookie_value=None,
            new_visitor_cookie=None,
        ),
    )
    monkeypatch.setattr(
        blog,
        "submit_image_comment",
        lambda image_id, visitor_identity, display_name, comment: {
            "id": 22,
            "commented_at": datetime(2026, 3, 26, 22, 15),
        },
    )
    monkeypatch.setattr(
        blog,
        "fetch_image_engagement_state",
        lambda image_id, visitor_identity, include_comments=False: {
            "liked": False,
            "like_count": 0,
            "view_count": 0,
            "comment_count": 3,
            "comments": [],
        },
    )

    with app.test_request_context(
        "/image/7/comment",
        method="POST",
        json={"display_name": "Grace", "comment": "Amazing framing.", "remember_name": True},
        environ_overrides={
            "HTTP_COOKIE": f"{COOKIE_CONSENT_COOKIE_NAME}={consent_cookie}",
        },
    ):
        response = blog.comment_on_image(7)

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["message"] == "Comment posted."
    assert payload["comment_count"] == 3
    assert payload["preferences_enabled"] is True
    assert payload["comment"]["display_name"] == "Grace"
    assert payload["comment"]["comment"] == "Amazing framing."
    assert "astrospace_commenter_name=Grace" in response.headers.get("Set-Cookie", "")


def test_comment_endpoint_returns_rate_limit_message(app, monkeypatch):
    from AstroSpace import blog

    monkeypatch.setattr(blog, "get_image_by_id", lambda image_id: {"id": image_id, "title": "Soul Nebula"})
    monkeypatch.setattr(
        blog,
        "build_visitor_identity",
        lambda: VisitorIdentity(
            visitor_hash="visitor-hash",
            visitor_source="network",
            ip_hash="ip-hash",
            user_agent_hash="ua-hash",
            visitor_cookie_hash=None,
            visitor_cookie_value=None,
            new_visitor_cookie=None,
        ),
    )
    monkeypatch.setattr(
        blog,
        "submit_image_comment",
        lambda image_id, visitor_identity, display_name, comment: (_ for _ in ()).throw(
            CommentRateLimitError("Please wait 60 seconds before posting another comment.")
        ),
    )

    with app.test_request_context(
        "/image/7/comment",
        method="POST",
        json={"display_name": "Grace", "comment": "Amazing framing.", "remember_name": False},
    ):
        response = app.make_response(blog.comment_on_image(7))

    assert response.status_code == 429
    assert response.get_json() == {
        "message": "Please wait 60 seconds before posting another comment."
    }
