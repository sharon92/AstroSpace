from io import BytesIO
from datetime import date

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


def test_save_image_persists_annotated_starless_and_related_media(app, monkeypatch):
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
    overlay_calls = []
    monkeypatch.setattr(
        blog, "get_overlays", lambda header_json: overlay_calls.append(header_json) or {"ok": True}
    )
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
            "annotated_image_path": (BytesIO(b"<svg xmlns='http://www.w3.org/2000/svg'/>"), "preview_annotated.svg"),
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
    assert image_insert[9].startswith("1/")
    assert image_insert[9].endswith("preview_annotated.svg")
    assert image_insert[14] is None
    assert overlay_calls == []
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
    assert '<span class="sr-only">Actions</span>' in html
    assert html.count('<option value="0" selected>None</option>') == 7


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
    assert "Upload Annotated Image" in html
    assert 'class="editor-assets-row"' in html
    assert 'class="editor-subsection editor-guide-logs"' in html
    assert 'id="relatedMediaInput"' in html
    assert 'name="starless_image_path"' in html
    assert 'name="related_media_store"' in html
    assert 'name="annotated_image_path"' in html
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

def test_edit_form_restores_saved_equipment_lights_and_metadata(app, monkeypatch):
    from AstroSpace import blog

    options = {
        "cam_filter": [{"id": 1, "name": "Ha"}],
        "reducer": [{"id": 12, "name": "Reducer"}],
        "filter_wheel": [{"id": 13, "name": "Filter wheel"}],
        "eaf": [{"id": 14, "name": "EAF"}],
        "dew_heater": [{"id": 15, "name": "Dew heater"}],
        "software": [{"id": 16, "name": "PixInsight"}],
    }
    monkeypatch.setattr(blog, "fetch_options", lambda table: options.get(table, []))
    monkeypatch.setattr(blog, "require_owner", lambda _author: None)

    image = {
        "id": 42,
        "author": "tester",
        "title": "Test target",
        "short_description": "Test",
        "description": "Test description",
        "image_path": "1/test.jpg",
        "starless_image_path": "",
        "location": "Backyard",
        "annotated_image_path": "1/test_annotated.jpg",
        "location_latitude": 1.0,
        "location_longitude": 2.0,
        "location_elevation": 3.0,
        "guide_log": "",
        "created_at": date(2026, 3, 19),
        "reducer_id": 12,
        "filter_wheel_id": 13,
        "eaf_id": 14,
        "dew_heater_id": 15,
    }
    for table in blog.DB_TABLES:
        image.setdefault(f"{table}_id", None)

    metadata = {
        "constant": {"FILTER": "Ha"},
        "variable": {"_files": ["light_001"], "WBPP weight 1": [1.5]},
        "comments": {"FILTER": "Filter used"},
    }
    tables = (
        image,
        [],
        [],
        [{"cam_filter": "Ha", "light_count": 10, "exposure_time": 300, "gain": 100, "offset_cam": 10, "temperature": -10}],
        [16],
        "",
        "",
        "",
        metadata,
        [],
    )
    monkeypatch.setattr(blog, "get_image_tables", lambda *_args, **_kwargs: tables)

    with app.test_request_context("/edit/42"):
        g.user = {"id": 1, "username": "tester", "admin": True}
        html = blog.edit_image.__wrapped__(42)

    assert '<option value="12" selected>Reducer' in html
    assert '<option value="13" selected>' in html
    assert '<option value="14" selected>EAF' in html
    assert '<option value="15" selected>' in html
    assert 'id="software-16" name="software_ids" type="checkbox" value="16"' in html
    assert 'id="software-16" name="software_ids" type="checkbox" value="16"\n                        checked' in html
    assert '<select name="software_ids"' not in html
    assert 'class="software-checkbox-grid"' in html
    assert 'const existingLights = [{"cam_filter": "Ha"' in html
    assert 'row.querySelector("select").value = light.cam_filter;' in html
    assert "js/binds.js?v=" in html
    assert 'const savedMetadata = {"comments": {"FILTER": "Filter used"}' in html
    assert "restoreMetadata(savedMetadata);" in html
    assert 'name="prev_annotated_img" value="1/test_annotated.jpg"' in html
    assert 'name="annotated_image_path"' in html
