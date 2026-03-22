from pathlib import Path


class FakeCursor:
    def __init__(self, db):
        self.db = db
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params=None):
        sql = str(query)
        self.db.executed.append((sql, params))
        if "SELECT id, guide_log" in sql:
            self.rows = list(self.db.guiding_rows)
        elif "SELECT id, image_path, header_json" in sql:
            self.rows = list(self.db.plate_rows)
        elif "SELECT image_path, image_thumbnail" in sql:
            self.rows = list(self.db.image_rows)
        elif "SELECT display_image" in sql:
            self.rows = list(self.db.user_rows)
        else:
            self.rows = []

    def fetchall(self):
        return self.rows


class FakeDB:
    def __init__(self, guiding_rows=None, plate_rows=None, image_rows=None, user_rows=None):
        self.guiding_rows = guiding_rows or []
        self.plate_rows = plate_rows or []
        self.image_rows = image_rows or []
        self.user_rows = user_rows or []
        self.executed = []
        self.commit_count = 0
        self.rollback_count = 0

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commit_count += 1

    def rollback(self):
        self.rollback_count += 1


def test_collect_orphan_image_uploads_only_returns_unreferenced_images(tmp_path):
    from AstroSpace.profile.private import collect_orphan_image_uploads

    upload_root = tmp_path / "uploads"
    user_dir = upload_root / "1"
    user_dir.mkdir(parents=True)

    keep = user_dir / "keep.jpg"
    thumb = user_dir / "keep_thumbnail.jpg"
    orphan = user_dir / "orphan.jpg"
    log_file = user_dir / "guide.txt"

    for path in [keep, thumb, orphan, log_file]:
        path.write_text("x", encoding="utf-8")

    orphans = collect_orphan_image_uploads(
        str(upload_root),
        {"1/keep.jpg", "1/keep_thumbnail.jpg"},
    )

    assert orphans == [str(orphan)]


def test_rebuild_all_guiding_plots_updates_images_with_existing_logs(tmp_path, monkeypatch):
    from AstroSpace.profile import private

    upload_root = tmp_path / "uploads"
    user_dir = upload_root / "1"
    user_dir.mkdir(parents=True)
    (user_dir / "guide1.txt").write_text("a", encoding="utf-8")
    (user_dir / "guide2.txt").write_text("b", encoding="utf-8")

    db = FakeDB(
        guiding_rows=[
            {"id": 7, "guide_log": "1/guide1.txt,1/guide2.txt"},
        ]
    )

    monkeypatch.setattr(
        private,
        "build_plotly_payloads",
        lambda paths: ({"kind": "guiding", "paths": paths}, {"kind": "calibration"}),
    )

    stats = private.rebuild_all_guiding_plots(db, str(upload_root))

    assert stats["updated"] == 1
    assert stats["skipped"] == 0
    assert db.commit_count == 1
    update_calls = [call for call in db.executed if "UPDATE images" in call[0]]
    assert len(update_calls) == 1
    assert update_calls[0][1][2] == 7


def test_rebuild_all_plate_solves_updates_images_with_existing_headers(app, tmp_path, monkeypatch):
    from AstroSpace.profile import private

    upload_root = tmp_path / "uploads"
    user_dir = upload_root / "1"
    user_dir.mkdir(parents=True)
    (user_dir / "image.png").write_text("image", encoding="utf-8")

    db = FakeDB(
        plate_rows=[
            {"id": 11, "image_path": "1/image.png", "header_json": "HEADER"},
        ]
    )

    monkeypatch.setattr(
        private,
        "rebuild_plate_solve_artifacts",
        lambda _abs_path, _public_path, _header_json: (
            "1/image_thumbnail.jpg",
            1.23,
            '{"ok": true}',
            "HEADER+DISPLAY",
        ),
    )

    with app.app_context():
        stats = private.rebuild_all_plate_solves(db, str(upload_root))

    assert stats["updated"] == 1
    assert stats["skipped"] == 0
    assert db.commit_count == 1
    update_calls = [call for call in db.executed if "UPDATE images" in call[0]]
    assert len(update_calls) == 1
    assert update_calls[0][1] == ("1/image_thumbnail.jpg", 1.23, '{"ok": true}', "HEADER+DISPLAY", 11)


def test_rebuild_all_plate_solves_skips_missing_image_files(app, tmp_path):
    from AstroSpace.profile.private import rebuild_all_plate_solves

    db = FakeDB(
        plate_rows=[
            {"id": 12, "image_path": "1/missing.jpg", "header_json": "HEADER"},
        ]
    )

    with app.app_context():
        stats = rebuild_all_plate_solves(db, str(tmp_path / "uploads"))

    assert stats["updated"] == 0
    assert stats["skipped"] == 1
    assert stats["missing_files"] == [{"image_id": 12, "path": "1/missing.jpg"}]
    assert db.commit_count == 0


def test_purge_unbound_image_uploads_deletes_only_unreferenced_files(tmp_path):
    from AstroSpace.profile.private import purge_unbound_image_uploads

    upload_root = tmp_path / "uploads"
    user_dir = upload_root / "1"
    user_dir.mkdir(parents=True)

    image_path = user_dir / "bound.jpg"
    thumb_path = user_dir / "bound_thumbnail.jpg"
    profile_thumb = user_dir / "profile_thumbnail.jpg"
    orphan_path = user_dir / "orphan.jpg"

    for path in [image_path, thumb_path, profile_thumb, orphan_path]:
        path.write_text("x", encoding="utf-8")

    db = FakeDB(
        image_rows=[{"image_path": "1/bound.jpg", "image_thumbnail": "1/bound_thumbnail.jpg"}],
        user_rows=[{"display_image": "1/profile_thumbnail.jpg"}],
    )

    stats = purge_unbound_image_uploads(db, str(upload_root))

    assert stats["deleted"] == 1
    assert stats["deleted_paths"] == ["1/orphan.jpg"]
    assert image_path.exists()
    assert thumb_path.exists()
    assert profile_thumb.exists()
    assert not orphan_path.exists()


def test_profile_template_includes_plate_solving_admin_action(app):
    from flask import render_template

    with app.test_request_context("/private/profile"):
        html = render_template(
            "profile.html",
            posts=[],
            inventory={},
            user_settings={},
            tabs=["Posts", "Inventory", "Settings"],
            data_type={},
            inventory_constraints={},
            WebName="AstroSpace Test",
            web_info={"site_name": "AstroSpace Test"},
            can_manage_site=True,
            active_tab="Settings",
        )

    assert "Redo plate solving for all images" in html
    assert "/private/admin/redo_plate_solving" in html
    assert "runRedoPlateSolvingOnce" in html
