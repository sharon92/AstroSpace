"""Add an optional pre-annotated image to posts."""

from alembic import op
import sqlalchemy as sa


revision = "20260816_0005"
down_revision = "20260326_0004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("images", sa.Column("annotated_image_path", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("images", "annotated_image_path")
