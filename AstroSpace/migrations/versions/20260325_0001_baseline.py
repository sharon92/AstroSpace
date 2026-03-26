"""Create the AstroSpace baseline schema."""

from pathlib import Path

from alembic import op


revision = "20260325_0001"
down_revision = None
branch_labels = None
depends_on = None


def _load_sql_snapshot():
    return Path(__file__).with_name("20260325_0001_baseline.sql").read_text(encoding="utf-8")


def upgrade():
    statements = [statement.strip() for statement in _load_sql_snapshot().split(";") if statement.strip()]
    for statement in statements:
        op.execute(statement)


def downgrade():
    op.execute(
        """
        DROP TABLE IF EXISTS
            camera,
            capture_dates,
            dew_heater,
            eaf,
            cam_filter,
            filter_wheel,
            rotator,
            flat_panel,
            image_lights,
            image_software,
            images,
            image_views,
            image_likes,
            image_comments,
            mount,
            guider,
            reducer,
            software,
            telescope,
            tripod,
            users,
            web_info
        CASCADE
        """
    )
