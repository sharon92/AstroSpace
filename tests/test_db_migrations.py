from AstroSpace import create_app
from AstroSpace import db
from AstroSpace.__main__ import handle_management_command
from flask import Flask


def make_app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DB_NAME": "astro space",
            "DB_USER": "astro-user",
            "DB_PASSWORD": "p@ss word",
            "DB_HOST": "localhost",
            "DB_PORT": 5432,
            "TITLE": "AstroSpace Test",
            "UPLOAD_PATH": str(tmp_path / "uploads"),
            "SKIP_DB_INIT": True,
        }
    )


def test_build_database_url_uses_psycopg2_scheme_and_quotes_credentials(tmp_path):
    app = make_app(tmp_path)

    with app.app_context():
        url = db.build_database_url()

    assert url == "postgresql+psycopg2://astro-user:p%40ss+word@localhost:5432/astro+space"


def test_build_database_url_works_without_flask_app_context(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DB_NAME", "astro_db")
    monkeypatch.setenv("DB_USER", "astro_user")
    monkeypatch.setenv("DB_PASSWORD", "astro password")
    monkeypatch.setenv("DB_HOST", "db.example")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("UPLOAD_PATH", str(tmp_path / "uploads"))

    url = db.build_database_url()

    assert url == "postgresql+psycopg2://astro_user:astro+password@db.example:5432/astro_db"


def test_get_db_config_loads_instance_config_without_flask_app_context(tmp_path, monkeypatch):
    instance_dir = tmp_path / "instance"
    instance_dir.mkdir()
    (instance_dir / "config.py").write_text(
        "\n".join(
            [
                "DB_NAME = 'instance_db'",
                "DB_USER = 'instance_user'",
                "DB_PASSWORD = 'instance_password'",
                "DB_HOST = 'instance_host'",
                "DB_PORT = 6543",
            ]
        ),
        encoding="utf-8",
    )

    for key in ("DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT"):
        monkeypatch.delenv(key, raising=False)

    def fake_flask(import_name, instance_relative_config=False):
        return Flask(
            import_name,
            instance_relative_config=instance_relative_config,
            instance_path=str(instance_dir),
        )

    monkeypatch.setattr("AstroSpace.db.Flask", fake_flask)

    db_config = db.get_db_config()

    assert db_config == {
        "dbname": "instance_db",
        "user": "instance_user",
        "password": "instance_password",
        "host": "instance_host",
        "port": 6543,
    }


def test_init_db_resets_public_schema_and_runs_alembic_upgrade(tmp_path, monkeypatch):
    app = make_app(tmp_path)
    executed = []
    upgrade_calls = []
    closed = []

    class DummyCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, statement):
            executed.append(" ".join(statement.split()))

    class DummyConnection:
        def __init__(self):
            self.committed = False

        def cursor(self):
            return DummyCursor()

        def commit(self):
            self.committed = True

    dummy_connection = DummyConnection()

    monkeypatch.setattr(db, "get_conn", lambda: dummy_connection)
    monkeypatch.setattr(db, "close_db", lambda e=None: closed.append(True))
    monkeypatch.setattr(db, "upgrade_db", lambda revision="head", config_source=None: upgrade_calls.append((revision, config_source)))

    with app.app_context():
        db.init_db()

    assert executed == [
        "DROP SCHEMA IF EXISTS public CASCADE",
        "CREATE SCHEMA public",
    ]
    assert dummy_connection.committed is True
    assert closed == [True]
    assert upgrade_calls == [("head", None)]


def test_classify_database_for_migrations_detects_legacy_schema():
    schema_snapshot = {
        "camera": {"id", "name"},
        "images": {"id", "title", "slug", "image_path", "image_thumbnail"},
        "software": {"id", "name", "type", "link", "metadata"},
        "telescope": {"id", "name"},
        "users": {"id", "username", "password", "admin"},
    }

    assert db.classify_database_for_migrations(schema_snapshot) == "legacy"


def test_ensure_database_revision_state_auto_stamps_legacy_schema(monkeypatch):
    states = []

    monkeypatch.setattr("AstroSpace.db.get_public_schema_snapshot", lambda config_source=None: {
        "camera": {"id", "name"},
        "images": {"id", "title", "slug", "image_path", "image_thumbnail"},
        "software": {"id", "name", "type", "link", "metadata"},
        "telescope": {"id", "name"},
        "users": {"id", "username", "password", "admin"},
    })
    monkeypatch.setattr("AstroSpace.db.stamp_db", lambda revision, config_source=None: states.append((revision, config_source)))

    result = db.ensure_database_revision_state()

    assert result == "stamped"
    assert states == [(db.BASELINE_MIGRATION_REVISION, None)]


def test_ensure_database_revision_state_rejects_unknown_non_empty_schema(monkeypatch):
    monkeypatch.setattr("AstroSpace.db.get_public_schema_snapshot", lambda config_source=None: {
        "random_table": {"id"},
    })

    try:
        db.ensure_database_revision_state()
    except RuntimeError as exc:
        assert "does not match the legacy AstroSpace schema" in str(exc)
    else:
        raise AssertionError("Expected ensure_database_revision_state() to reject unknown schemas.")


def test_handle_management_command_runs_migrate(monkeypatch):
    revisions = []

    monkeypatch.setattr("AstroSpace.__main__.upgrade_db", lambda revision="head": revisions.append(revision))

    assert handle_management_command(["migrate"]) is True
    assert revisions == ["head"]


def test_handle_management_command_runs_stamp(monkeypatch):
    revisions = []

    monkeypatch.setattr("AstroSpace.__main__.stamp_db", lambda revision: revisions.append(revision))

    assert handle_management_command(["stamp", "custom_rev"]) is True
    assert revisions == ["custom_rev"]


def test_handle_management_command_returns_false_for_web_args():
    assert handle_management_command(["--debug"]) is False
