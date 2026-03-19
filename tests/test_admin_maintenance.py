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
        elif "SELECT image_path, image_thumbnail" in sql:
            self.rows = list(self.db.image_rows)
        elif "SELECT display_image" in sql:
            self.rows = list(self.db.user_rows)
        else:
            self.rows = []

    def fetchall(self):
        return self.rows


class FakeDB:
    def __init__(self, guiding_rows=None, image_rows=None, user_rows=None):
        self.guiding_rows = guiding_rows or []
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
