import logging
import os
from pathlib import Path
from urllib.parse import quote_plus

import click
from flask import Flask
from flask import current_app, g
import psycopg2
from psycopg2.extras import RealDictCursor

from AstroSpace.logging_utils import debug_log


BASELINE_MIGRATION_REVISION = "20260325_0001"
DEFAULT_MIGRATION_REVISION = "head"
ALEMBIC_CONFIG_PATH = Path(__file__).resolve().with_name("alembic.ini")
ALEMBIC_SCRIPT_PATH = Path(__file__).resolve().parent / "migrations"
LEGACY_BASELINE_TABLES = {"camera", "images", "software", "telescope", "users"}
LEGACY_BASELINE_COLUMNS = {
    "images": {"title", "slug", "image_path", "image_thumbnail"},
    "software": {"name", "type", "link", "metadata"},
    "users": {"username", "password", "admin"},
}


def load_runtime_config(config_source=None):
    if config_source is not None:
        return config_source

    env_keys = ("DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT")
    if all(key in os.environ for key in env_keys):
        return {
            "DB_NAME": os.environ["DB_NAME"],
            "DB_USER": os.environ["DB_USER"],
            "DB_PASSWORD": os.environ["DB_PASSWORD"],
            "DB_HOST": os.environ["DB_HOST"],
            "DB_PORT": int(os.environ["DB_PORT"]),
        }

    try:
        return current_app.config
    except RuntimeError:
        app = Flask("AstroSpace", instance_relative_config=True)
        app.config.from_object("AstroSpace.config.Config")
        app.config.from_envvar("ASTROSPACE_SETTINGS", silent=True)
        app.config.from_pyfile("config.py", silent=True)
        return app.config


def get_db_config(config_source=None):
    source = load_runtime_config(config_source)
    return {
        "dbname": source["DB_NAME"],
        "user": source["DB_USER"],
        "password": source["DB_PASSWORD"],
        "host": source["DB_HOST"],
        "port": source["DB_PORT"],
    }


def build_database_url(config_source=None):
    db_config = get_db_config(config_source)
    user = quote_plus(str(db_config["user"]))
    password = quote_plus(str(db_config["password"]))
    host = db_config["host"]
    port = db_config["port"]
    dbname = quote_plus(str(db_config["dbname"]))
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"


def get_alembic_config(config_source=None):
    from alembic.config import Config

    alembic_config = Config(str(ALEMBIC_CONFIG_PATH))
    alembic_config.set_main_option("script_location", str(ALEMBIC_SCRIPT_PATH))
    alembic_config.set_main_option("sqlalchemy.url", build_database_url(config_source))
    return alembic_config


def get_public_schema_snapshot(config_source=None):
    db_config = {
        **get_db_config(config_source),
        "cursor_factory": RealDictCursor,
    }
    connection = psycopg2.connect(**db_config)
    try:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position
                """
            )
            rows = cur.fetchall()
    finally:
        connection.close()

    tables = {}
    for row in rows:
        table_name = row["table_name"]
        tables.setdefault(table_name, set()).add(row["column_name"])
    return tables


def classify_database_for_migrations(schema_snapshot):
    tables = set(schema_snapshot)
    if "alembic_version" in tables:
        return "migrated"

    if not tables:
        return "empty"

    if LEGACY_BASELINE_TABLES.issubset(tables):
        for table_name, required_columns in LEGACY_BASELINE_COLUMNS.items():
            if not required_columns.issubset(schema_snapshot.get(table_name, set())):
                return "unknown"
        return "legacy"

    return "unknown"


def ensure_database_revision_state(config_source=None):
    schema_snapshot = get_public_schema_snapshot(config_source)
    state = classify_database_for_migrations(schema_snapshot)

    if state == "legacy":
        debug_log(
            "Detected legacy AstroSpace schema without Alembic history; stamping revision=%s before upgrade.",
            BASELINE_MIGRATION_REVISION,
            level=logging.INFO,
        )
        stamp_db(revision=BASELINE_MIGRATION_REVISION, config_source=config_source)
        return "stamped"

    if state == "unknown":
        raise RuntimeError(
            "Database contains tables but no Alembic history and does not match the legacy AstroSpace schema. "
            "Back up the database and run a manual stamp only after verifying the schema."
        )

    return state


def upgrade_db(revision=DEFAULT_MIGRATION_REVISION, config_source=None):
    from alembic import command

    state = ensure_database_revision_state(config_source)
    debug_log("Applying Alembic migrations up to revision=%s", revision, level=logging.INFO)
    debug_log("Database migration readiness state=%s", state)
    command.upgrade(get_alembic_config(config_source), revision)


def stamp_db(revision=BASELINE_MIGRATION_REVISION, config_source=None):
    from alembic import command

    debug_log("Stamping database with Alembic revision=%s", revision, level=logging.INFO)
    command.stamp(get_alembic_config(config_source), revision)


def get_conn():
    if "db" not in g:
        db_config = {
            **get_db_config(),
            "cursor_factory": RealDictCursor,
        }
        debug_log(
            "Opening PostgreSQL connection to %s:%s/%s as %s",
            db_config["host"],
            db_config["port"],
            db_config["dbname"],
            db_config["user"],
        )
        g.db = psycopg2.connect(**db_config)

    return g.db


def check_images_table_exists():
    db = get_conn()
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'images'
            );
            """
        )
        return cur.fetchone()["exists"]


def close_db(e=None):
    db = g.pop("db", None)

    if db is not None:
        debug_log("Closing PostgreSQL connection.")
        db.close()


def init_db():
    db = get_conn()
    debug_log("Resetting public schema before applying Alembic migrations.", level=logging.INFO)

    with db.cursor() as cur:
        cur.execute("DROP SCHEMA IF EXISTS public CASCADE")
        cur.execute("CREATE SCHEMA public")
    db.commit()
    close_db()
    upgrade_db()


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(migrate_db_command)
    app.cli.add_command(stamp_db_command)


@click.command("init-db")
def init_db_command():
    """Clear the existing data and recreate it via Alembic migrations."""
    init_db()
    click.echo("Initialized the database.")


@click.command("migrate-db")
@click.option("--revision", default=DEFAULT_MIGRATION_REVISION, show_default=True)
def migrate_db_command(revision):
    """Apply Alembic migrations."""
    upgrade_db(revision=revision)
    click.echo(f"Migrated database to {revision}.")


@click.command("stamp-db")
@click.option("--revision", default=BASELINE_MIGRATION_REVISION, show_default=True)
def stamp_db_command(revision):
    """Mark an existing database with an Alembic revision without running migrations."""
    stamp_db(revision=revision)
    click.echo(f"Stamped database with {revision}.")
