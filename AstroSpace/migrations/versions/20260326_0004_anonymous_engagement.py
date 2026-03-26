"""Upgrade engagement tables for anonymous cookies and privacy-safe hashing."""

from alembic import op
import sqlalchemy as sa


revision = "20260326_0004"
down_revision = "20260326_0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("image_views", sa.Column("visitor_hash", sa.Text(), nullable=True))
    op.add_column(
        "image_views",
        sa.Column("visitor_source", sa.Text(), nullable=False, server_default="network"),
    )
    op.add_column("image_views", sa.Column("ip_hash", sa.Text(), nullable=True))
    op.add_column("image_views", sa.Column("user_agent_hash", sa.Text(), nullable=True))
    op.add_column("image_views", sa.Column("visitor_cookie_hash", sa.Text(), nullable=True))
    op.add_column(
        "image_views",
        sa.Column(
            "last_seen_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.execute(
        """
        UPDATE image_views
        SET visitor_hash = COALESCE(NULLIF(BTRIM(user_id), ''), 'legacy-view-' || id::text),
            visitor_source = 'legacy',
            ip_hash = NULL,
            user_agent_hash = NULL,
            visitor_cookie_hash = NULL,
            last_seen_at = COALESCE(viewed_at, CURRENT_TIMESTAMP)
        WHERE visitor_hash IS NULL
        """
    )
    op.execute(
        """
        DELETE FROM image_views older
        USING image_views newer
        WHERE older.id < newer.id
          AND older.image_id = newer.image_id
          AND older.visitor_hash = newer.visitor_hash
        """
    )
    op.alter_column("image_views", "visitor_hash", nullable=False)
    op.create_unique_constraint(
        "uq_image_views_image_visitor_hash",
        "image_views",
        ["image_id", "visitor_hash"],
    )
    op.create_index("ix_image_views_image_id", "image_views", ["image_id"])

    op.add_column("image_likes", sa.Column("visitor_hash", sa.Text(), nullable=True))
    op.add_column(
        "image_likes",
        sa.Column("visitor_source", sa.Text(), nullable=False, server_default="network"),
    )
    op.add_column("image_likes", sa.Column("ip_hash", sa.Text(), nullable=True))
    op.add_column("image_likes", sa.Column("user_agent_hash", sa.Text(), nullable=True))
    op.add_column("image_likes", sa.Column("visitor_cookie_hash", sa.Text(), nullable=True))
    op.execute(
        """
        UPDATE image_likes
        SET visitor_hash = COALESCE(NULLIF(BTRIM(user_id), ''), 'legacy-like-' || id::text),
            visitor_source = 'legacy'
        WHERE visitor_hash IS NULL
        """
    )
    op.alter_column("image_likes", "visitor_hash", nullable=False)
    op.execute(
        "ALTER TABLE image_likes DROP CONSTRAINT IF EXISTS image_likes_image_id_user_id_key"
    )
    op.create_unique_constraint(
        "uq_image_likes_image_visitor_hash",
        "image_likes",
        ["image_id", "visitor_hash"],
    )
    op.create_index("ix_image_likes_image_id", "image_likes", ["image_id"])

    op.add_column("image_comments", sa.Column("visitor_hash", sa.Text(), nullable=True))
    op.add_column(
        "image_comments",
        sa.Column("visitor_source", sa.Text(), nullable=False, server_default="legacy"),
    )
    op.add_column("image_comments", sa.Column("ip_hash", sa.Text(), nullable=True))
    op.add_column("image_comments", sa.Column("user_agent_hash", sa.Text(), nullable=True))
    op.add_column("image_comments", sa.Column("visitor_cookie_hash", sa.Text(), nullable=True))
    op.add_column(
        "image_comments",
        sa.Column("status", sa.Text(), nullable=False, server_default="published"),
    )
    op.execute(
        """
        UPDATE image_comments
        SET visitor_hash = COALESCE(NULLIF(BTRIM(ip_address), ''), 'legacy-comment-' || id::text),
            visitor_source = 'legacy',
            ip_hash = CASE
                WHEN NULLIF(BTRIM(ip_address), '') IS NULL THEN NULL
                ELSE md5(ip_address)
            END,
            ip_address = CASE
                WHEN NULLIF(BTRIM(ip_address), '') IS NULL THEN NULL
                ELSE md5(ip_address)
            END,
            status = 'published'
        WHERE visitor_hash IS NULL
        """
    )
    op.alter_column("image_comments", "visitor_hash", nullable=False)
    op.create_index(
        "ix_image_comments_image_status",
        "image_comments",
        ["image_id", "status"],
    )
    op.create_index(
        "ix_image_comments_visitor_hash_commented_at",
        "image_comments",
        ["visitor_hash", "commented_at"],
    )


def downgrade():
    op.drop_index("ix_image_comments_visitor_hash_commented_at", table_name="image_comments")
    op.drop_index("ix_image_comments_image_status", table_name="image_comments")
    op.drop_column("image_comments", "status")
    op.drop_column("image_comments", "visitor_cookie_hash")
    op.drop_column("image_comments", "user_agent_hash")
    op.drop_column("image_comments", "ip_hash")
    op.drop_column("image_comments", "visitor_source")
    op.drop_column("image_comments", "visitor_hash")

    op.drop_index("ix_image_likes_image_id", table_name="image_likes")
    op.drop_constraint("uq_image_likes_image_visitor_hash", "image_likes", type_="unique")
    op.create_unique_constraint(
        "image_likes_image_id_user_id_key",
        "image_likes",
        ["image_id", "user_id"],
    )
    op.drop_column("image_likes", "visitor_cookie_hash")
    op.drop_column("image_likes", "user_agent_hash")
    op.drop_column("image_likes", "ip_hash")
    op.drop_column("image_likes", "visitor_source")
    op.drop_column("image_likes", "visitor_hash")

    op.drop_index("ix_image_views_image_id", table_name="image_views")
    op.drop_constraint("uq_image_views_image_visitor_hash", "image_views", type_="unique")
    op.drop_column("image_views", "last_seen_at")
    op.drop_column("image_views", "visitor_cookie_hash")
    op.drop_column("image_views", "user_agent_hash")
    op.drop_column("image_views", "ip_hash")
    op.drop_column("image_views", "visitor_source")
    op.drop_column("image_views", "visitor_hash")
