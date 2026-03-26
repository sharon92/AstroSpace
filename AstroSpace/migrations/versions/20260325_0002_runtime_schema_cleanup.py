"""Fold legacy runtime schema updates into Alembic."""

import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260325_0002"
down_revision = "20260325_0001"
branch_labels = None
depends_on = None


USER_TEXT_COLUMNS = (
    "display_name",
    "display_image",
    "bio",
    "astrometry_api_key",
    "open_weather_api_key",
    "telescopius_api_key",
)

WEB_INFO_COLUMNS = {
    "site_name": sa.Text(),
    "site_description": sa.Text(),
    "welcome_message": sa.Text(),
    "contact_email": sa.Text(),
    "social_links": postgresql.JSONB(astext_type=sa.Text()),
}

PLOT_COLUMN_MIGRATIONS = (
    ("guiding_html", "guiding_plot_json", "Guiding"),
    ("calibration_html", "calibration_plot_json", "Calibration"),
)


def _legacy_plot_payload(title):
    return {
        "kind": title.lower(),
        "legacy": True,
        "message": f"{title} plot was generated with a legacy renderer. Re-save the image to regenerate it.",
    }


def _table_exists(bind, table_name):
    return table_name in sa.inspect(bind).get_table_names(schema="public")


def _columns_by_name(bind, table_name):
    return {
        column["name"]: column
        for column in sa.inspect(bind).get_columns(table_name, schema="public")
    }


def _is_jsonb(column):
    return isinstance(column["type"], postgresql.JSONB)


def _coerce_legacy_plot_sql(column_name, fallback_json):
    escaped_fallback = fallback_json.replace("'", "''")
    return f"""
        CASE
            WHEN {column_name} IS NULL OR NULLIF(BTRIM({column_name}::text), '') IS NULL THEN NULL
            WHEN LEFT(LTRIM({column_name}::text), 1) IN ('{{', '[') THEN ({column_name}::text)::jsonb
            ELSE '{escaped_fallback}'::jsonb
        END
    """


def _ensure_users_columns(bind):
    columns = _columns_by_name(bind, "users")
    for column_name in USER_TEXT_COLUMNS:
        if column_name not in columns:
            op.add_column("users", sa.Column(column_name, sa.Text(), nullable=True))


def _ensure_web_info(bind):
    if not _table_exists(bind, "web_info"):
        op.create_table(
            "web_info",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("site_name", sa.Text(), nullable=True),
            sa.Column("site_description", sa.Text(), nullable=True),
            sa.Column("welcome_message", sa.Text(), nullable=True),
            sa.Column("contact_email", sa.Text(), nullable=True),
            sa.Column("social_links", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )
        return

    columns = _columns_by_name(bind, "web_info")
    for column_name, column_type in WEB_INFO_COLUMNS.items():
        if column_name not in columns:
            op.add_column("web_info", sa.Column(column_name, column_type, nullable=True))


def _ensure_plot_columns(bind):
    columns = _columns_by_name(bind, "images")

    for legacy_column, target_column, title in PLOT_COLUMN_MIGRATIONS:
        fallback_json = json.dumps(_legacy_plot_payload(title))

        if target_column not in columns:
            op.add_column(
                "images",
                sa.Column(target_column, postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            )
            columns = _columns_by_name(bind, "images")
        elif not _is_jsonb(columns[target_column]):
            op.execute(
                f"""
                ALTER TABLE images
                ALTER COLUMN {target_column} TYPE JSONB
                USING {_coerce_legacy_plot_sql(target_column, fallback_json)}
                """
            )
            columns = _columns_by_name(bind, "images")

        if legacy_column in columns:
            op.execute(
                f"""
                UPDATE images
                SET {target_column} = COALESCE(
                    {target_column},
                    {_coerce_legacy_plot_sql(legacy_column, fallback_json)}
                )
                WHERE {legacy_column} IS NOT NULL
                """
            )
            op.drop_column("images", legacy_column)
            columns = _columns_by_name(bind, "images")


def upgrade():
    bind = op.get_bind()

    if _table_exists(bind, "users"):
        _ensure_users_columns(bind)

    _ensure_web_info(bind)

    if _table_exists(bind, "images"):
        _ensure_plot_columns(bind)


def downgrade():
    # This revision folds ad hoc runtime schema mutations into explicit migration history.
    # It is intentionally not reversed automatically.
    pass
