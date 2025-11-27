from flask import Blueprint, render_template
from AstroSpace.utils.queries import get_conn

bp = Blueprint("profile", __name__, url_prefix="/profile")

@bp.route("/<username>", endpoint="public")
def public_profile(username):
    db = get_conn()

    # --- Get user info ---
    with db.cursor() as cur:
        cur.execute("""
            SELECT username, display_image, bio, display_name
            FROM users
            WHERE username = %s
        """, (username,))
        user = cur.fetchone()

    if not user:
        return render_template("404.html"), 404

    # --- Get user's posts ---
    with db.cursor() as cur:
        cur.execute("""
            SELECT id, title, short_description, image_thumbnail, slug
            FROM images
            WHERE author = %s
            ORDER BY created_at DESC
        """, (username,))
        posts = cur.fetchall()

    return render_template(
        "public_profile.html",
        user=user,
        posts=posts
    )
