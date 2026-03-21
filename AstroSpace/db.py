import json
import logging

import click
from flask import current_app, g
import psycopg2
from psycopg2.extras import RealDictCursor

from AstroSpace.logging_utils import debug_log
from AstroSpace.utils.phd2logparser import legacy_plot_payload


PLOT_COLUMN_MIGRATIONS = (
    ("guiding_html", "guiding_plot_json", "Guiding"),
    ("calibration_html", "calibration_plot_json", "Calibration"),
)

def get_conn():
    if 'db' not in g:
        # Database configuration
        db_config = {
            'dbname': current_app.config['DB_NAME'],
            'user': current_app.config['DB_USER'],
            'password': current_app.config['DB_PASSWORD'],
            'host': current_app.config['DB_HOST'],
            'port': current_app.config['DB_PORT'],
            'cursor_factory': RealDictCursor
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
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'images'
            );
        """)
        return cur.fetchone()['exists']


def _get_column_type(cur, table_name, column_name):
    cur.execute(
        """
        SELECT data_type
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s AND column_name = %s
        """,
        (table_name, column_name),
    )
    row = cur.fetchone()
    return row["data_type"] if row else None


def _coerce_legacy_plot_sql(column_name):
    return f"""
        CASE
            WHEN {column_name} IS NULL OR NULLIF(BTRIM({column_name}::text), '') IS NULL THEN NULL
            WHEN LEFT(LTRIM({column_name}::text), 1) IN ('{{', '[') THEN ({column_name}::text)::jsonb
            ELSE %s::jsonb
        END
    """


def ensure_runtime_schema():
    db = get_conn()
    with db.cursor() as cur:
        for legacy_column, target_column, title in PLOT_COLUMN_MIGRATIONS:
            target_type = _get_column_type(cur, "images", target_column)
            legacy_type = _get_column_type(cur, "images", legacy_column)

            if target_type is None:
                debug_log(
                    "Adding missing runtime column images.%s",
                    target_column,
                    level=logging.INFO,
                )
                cur.execute(f"ALTER TABLE images ADD COLUMN {target_column} JSONB")
            elif target_type != "jsonb":
                debug_log(
                    "Converting images.%s from %s to jsonb",
                    target_column,
                    target_type,
                    level=logging.INFO,
                )
                cur.execute(
                    f"""
                    ALTER TABLE images
                    ALTER COLUMN {target_column} TYPE JSONB
                    USING {_coerce_legacy_plot_sql(target_column)}
                    """,
                    (json.dumps(legacy_plot_payload(title)),),
                )

            if legacy_type is not None:
                debug_log(
                    "Migrating legacy plot column images.%s into images.%s",
                    legacy_column,
                    target_column,
                    level=logging.INFO,
                )
                cur.execute(
                    f"""
                    UPDATE images
                    SET {target_column} = COALESCE(
                        {target_column},
                        {_coerce_legacy_plot_sql(legacy_column)}
                    )
                    WHERE {legacy_column} IS NOT NULL
                    """,
                    (json.dumps(legacy_plot_payload(title)),),
                )
                cur.execute(f"ALTER TABLE images DROP COLUMN {legacy_column}")

    db.commit()
    debug_log("Runtime schema check completed successfully.")

def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        debug_log("Closing PostgreSQL connection.")
        db.close()

def init_db():
    db = get_conn()

    with current_app.open_resource('schema.sql') as f:
        sql_statements = f.read().decode('utf8')
        statements = [statement.strip() for statement in sql_statements.split(';') if statement.strip()]
        debug_log(
            "Initializing database schema with %s SQL statements.",
            len(statements),
            level=logging.INFO,
        )
        
        with db.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
            db.commit()

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')
