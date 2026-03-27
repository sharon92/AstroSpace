from datetime import datetime

from AstroSpace.services.engagement import VisitorIdentity


class _FakeCursor:
    def execute(self, query, params=None):
        self.query = query
        self.params = params

    def fetchall(self):
        return []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeConnection:
    def cursor(self):
        return _FakeCursor()


def test_image_detail_route_includes_previous_and_next_unique_posts(app, monkeypatch):
    from AstroSpace import blog

    captured = {}
    current_image = {
        "id": 2,
        "title": "NGC 2548",
        "slug": "ngc-2548",
        "image_path": "uploads/ngc-2548.jpg",
        "created_at": datetime(2026, 2, 1),
        "author": "sharon",
    }

    monkeypatch.setattr(blog, "IMAGE_DETAIL_TABLE_NAMES", ["image", "lights"])
    monkeypatch.setattr(blog, "get_image_tables", lambda image_id: [current_image, []])
    monkeypatch.setattr(
        blog,
        "get_all_images",
        lambda unique=False, limit=None: [
            {"id": 1, "slug": "m42", "title": "M42"},
            {"id": 2, "slug": "ngc-2548", "title": "NGC 2548"},
            {"id": 3, "slug": "rosette", "title": "Rosette"},
        ],
    )
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
    monkeypatch.setattr(blog, "record_image_view", lambda image_id, visitor_identity: None)
    monkeypatch.setattr(
        blog,
        "fetch_image_engagement_state",
        lambda image_id, visitor_identity, include_comments=True: {
            "liked": False,
            "like_count": 0,
            "view_count": 0,
            "comment_count": 0,
            "comments": [],
        },
    )
    monkeypatch.setattr(blog, "get_conn", lambda: _FakeConnection())
    monkeypatch.setattr(blog, "commenter_name_from_request", lambda: "")
    monkeypatch.setattr(blog, "consent_allows", lambda category: False)
    monkeypatch.setattr(blog, "apply_visitor_cookie", lambda response, visitor_identity: None)

    def fake_render(template_name, **kwargs):
        captured["template_name"] = template_name
        captured.update(kwargs)
        return "ok"

    monkeypatch.setattr(blog, "render_template", fake_render)

    with app.test_request_context("/image/2/ngc-2548"):
        response = blog.image_detail(2, "ngc-2548")

    assert response.get_data(as_text=True) == "ok"
    assert captured["template_name"] == "image_detail.html"
    assert captured["previous_post"]["id"] == 1
    assert captured["previous_post"]["slug"] == "m42"
    assert captured["next_post"]["id"] == 3
    assert captured["next_post"]["slug"] == "rosette"
