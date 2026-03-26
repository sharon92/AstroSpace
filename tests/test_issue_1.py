from io import BytesIO

from flask import g


class FakeInventoryCursor:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params=None):
        self.conn.executed.append((query, params))

    def fetchone(self):
        return {"id": 99}

    def close(self):
        return None


class FakeInventoryConnection:
    def __init__(self):
        self.executed = []
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return FakeInventoryCursor(self)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def test_save_image_redirects_when_preview_image_is_missing(app, monkeypatch):
    from AstroSpace import blog

    monkeypatch.setattr(blog, "geocode", lambda _location: (51.0, 7.0))
    monkeypatch.setattr(blog.Simbad, "reset_votable_fields", lambda: None)
    monkeypatch.setattr(blog.Simbad, "add_votable_fields", lambda *_args: None)
    monkeypatch.setattr(blog.Simbad, "query_object", lambda _title: None)

    with app.test_request_context(
        "/create",
        method="POST",
        data={
            "title": "North America Nebula",
            "short_description": "Test",
            "description": "Test description",
            "location": "Backyard",
            "created_at": "2026-03-19",
        },
    ):
        g.user = {"id": 1, "username": "tester", "admin": True}

        response = blog.save_image()

    assert response.status_code == 302
    assert response.location.endswith("/new")


def test_save_image_accepts_png_preview(app, monkeypatch):
    from AstroSpace import blog

    conn = FakeInventoryConnection()
    monkeypatch.setattr(blog, "get_conn", lambda: conn)
    monkeypatch.setattr(blog, "geocode", lambda _location: (51.0, 7.0))
    monkeypatch.setattr(blog.Simbad, "reset_votable_fields", lambda: None)
    monkeypatch.setattr(blog.Simbad, "add_votable_fields", lambda *_args: None)
    monkeypatch.setattr(blog.Simbad, "query_object", lambda _title: None)
    monkeypatch.setattr(
        blog,
        "platesolve",
        lambda _image_path, _user_id, _fits_file: ("HEADER", "1/test_thumbnail.jpg", 1.23),
    )
    monkeypatch.setattr(blog, "get_overlays", lambda _header_json: {"ok": True})
    monkeypatch.setattr(blog, "sanitize_rich_text", lambda value: value)
    monkeypatch.setattr(blog, "parse_meta_store", lambda _value: "{}")

    with app.test_request_context(
        "/create",
        method="POST",
        data={
            "title": "North America Nebula",
            "short_description": "Test",
            "description": "Test description",
            "location": "Backyard",
            "created_at": "2026-03-19",
            "image_path": (BytesIO(b"png-bytes"), "preview.png"),
            "fits_file": (BytesIO(b"fits-bytes"), "capture.fits"),
        },
    ):
        g.user = {
            "id": 1,
            "username": "tester",
            "admin": True,
            "astrometry_api_key": "",
        }

        response = blog.save_image()

    assert response.status_code == 302
    assert response.location.endswith("/private/profile?tab=Posts")
    assert conn.committed is True
    assert any("INSERT INTO images" in query for query, _params in conn.executed)


def test_save_image_persists_starless_and_related_media(app, monkeypatch):
    from AstroSpace import blog

    conn = FakeInventoryConnection()
    monkeypatch.setattr(blog, "get_conn", lambda: conn)
    monkeypatch.setattr(blog, "geocode", lambda _location: (51.0, 7.0))
    monkeypatch.setattr(blog.Simbad, "reset_votable_fields", lambda: None)
    monkeypatch.setattr(blog.Simbad, "add_votable_fields", lambda *_args: None)
    monkeypatch.setattr(blog.Simbad, "query_object", lambda _title: None)
    monkeypatch.setattr(
        blog,
        "platesolve",
        lambda _image_path, _user_id, _fits_file: ("HEADER", "1/test_thumbnail.jpg", 1.23),
    )
    monkeypatch.setattr(blog, "get_overlays", lambda _header_json: {"ok": True})
    monkeypatch.setattr(blog, "sanitize_rich_text", lambda value: value)
    monkeypatch.setattr(blog, "parse_meta_store", lambda _value: "{}")

    with app.test_request_context(
        "/create",
        method="POST",
        data={
            "title": "Rosette Nebula",
            "short_description": "With starless",
            "description": "Test description",
            "location": "Backyard",
            "created_at": "2026-03-19",
            "related_media_store": '[{"existing_path":"","caption":"Setup timelapse"}]',
            "image_path": (BytesIO(b"png-bytes"), "preview.png"),
            "starless_image_path": (BytesIO(b"starless-bytes"), "preview_starless.png"),
            "fits_file": (BytesIO(b"fits-bytes"), "capture.fits"),
            "related_media_files": (BytesIO(b"video-bytes"), "setup.mp4"),
        },
    ):
        g.user = {
            "id": 1,
            "username": "tester",
            "admin": True,
            "astrometry_api_key": "",
        }

        response = blog.save_image()

    assert response.status_code == 302
    image_insert = next(params for query, params in conn.executed if "INSERT INTO images" in query)
    assert image_insert[8].startswith("1/")
    assert image_insert[8].endswith("preview_starless.png")
    related_insert = next(params for query, params in conn.executed if "INSERT INTO related_image_media" in query)
    assert related_insert[1].startswith("1/")
    assert related_insert[1].endswith("setup.mp4")
    assert related_insert[2] == "Setup timelapse"


def test_render_image_form_includes_light_headers(app, monkeypatch):
    from AstroSpace import blog

    monkeypatch.setattr(blog, "fetch_options", lambda _table: [])

    with app.test_request_context("/new"):
        html = blog.render_image_form(
            "New Post",
            equipment={},
            capture_dates=[],
            software_list=[],
            lights_json="[]",
            is_edit=False,
        )

    assert 'id="lightsTable"' in html
    assert 'id="lightsHeader"' in html
    assert "Frames" in html
    assert "Exposure (s)" in html
    assert "Temp (C)" in html
    assert "<th class=\"w-24 text-left font-semibold\"></th>" in html


def test_render_image_form_includes_starless_and_related_media_uploads(app, monkeypatch):
    from AstroSpace import blog

    monkeypatch.setattr(blog, "fetch_options", lambda _table: [])

    with app.test_request_context("/new"):
        html = blog.render_image_form(
            "New Post",
            equipment={},
            capture_dates=[],
            software_list=[],
            lights_json="[]",
            related_media_json="[]",
            is_edit=False,
        )

    assert "Upload Image" in html
    assert "Upload FITS/XISF" in html
    assert "Upload Starless Image" in html
    assert "Upload Other Related Media" in html
    assert 'id="relatedMediaInput"' in html
    assert 'name="starless_image_path"' in html
    assert 'name="related_media_store"' in html
    assert "Image Added" in html
    assert "Optional caption" in html


def test_update_inventory_normalizes_constrained_values(app, monkeypatch):
    from AstroSpace.profile import private

    conn = FakeInventoryConnection()
    monkeypatch.setattr(private, "get_conn", lambda: conn)

    with app.test_request_context(
        "/private/update_inventory",
        method="POST",
        json={
            "type": "telescope",
            "values": {
                "id": -1,
                "name": "Northstar",
                "type": "Reflector",
                "aperture": "114",
            },
        },
    ):
        g.user = {"id": 1, "username": "tester", "admin": True}
        response = app.make_response(private.update_inventory())

    assert response.status_code == 200
    assert conn.committed is True
    assert "reflector" in conn.executed[0][1]


def test_update_inventory_rejects_blank_names(app, monkeypatch):
    from AstroSpace.profile import private

    conn = FakeInventoryConnection()
    monkeypatch.setattr(private, "get_conn", lambda: conn)

    with app.test_request_context(
        "/private/update_inventory",
        method="POST",
        json={
            "type": "cam_filter",
            "values": {
                "id": -1,
                "name": "   ",
                "type": "",
            },
        },
    ):
        g.user = {"id": 1, "username": "tester", "admin": True}
        response = app.make_response(private.update_inventory())

    assert response.status_code == 400
    assert response.get_json()["message"] == "Name is required."
    assert conn.committed is False
