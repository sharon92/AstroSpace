"""Add starless preview support and related image media."""

from alembic import op
import sqlalchemy as sa


revision = "20260326_0003"
down_revision = "20260325_0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("images", sa.Column("starless_image_path", sa.Text(), nullable=True))
    op.create_table(
        "related_image_media",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("image_id", sa.Integer(), sa.ForeignKey("images.id", ondelete="CASCADE"), nullable=False),
        sa.Column("media_path", sa.Text(), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )


def downgrade():
    op.drop_table("related_image_media")
    op.drop_column("images", "starless_image_path")
