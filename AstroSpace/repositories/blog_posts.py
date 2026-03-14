import json

from AstroSpace.db import get_conn
from AstroSpace.utils.utils import slugify


def _hydrate_blog(row):
    metadata = {}
    raw_metadata = row.get("metadata")
    if raw_metadata:
        try:
            metadata = json.loads(raw_metadata)
        except json.JSONDecodeError:
            metadata = {}

    hydrated = dict(row)
    hydrated.update(metadata)
    hydrated.setdefault("slug", slugify(hydrated.get("title", f"blog-{row['id']}")))
    hydrated.setdefault("excerpt", "")
    hydrated.setdefault("author", "")
    hydrated.setdefault("image_path", "")
    hydrated.setdefault("image_thumbnail", "")
    hydrated.setdefault("content_html", row.get("blog_html", ""))
    return hydrated


def list_blogs(limit=None):
    conn = get_conn()
    cur = conn.cursor()
    if limit is None:
        cur.execute("SELECT * FROM blogs ORDER BY created_at DESC")
    else:
        cur.execute("SELECT * FROM blogs ORDER BY created_at DESC LIMIT %s", (limit,))
    return [_hydrate_blog(row) for row in cur.fetchall()]


def get_blog_by_id(blog_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM blogs WHERE id = %s", (blog_id,))
    row = cur.fetchone()
    return _hydrate_blog(row) if row else None


def get_blog_by_slug(slug):
    for blog in list_blogs():
        if blog["slug"] == slug:
            return blog
    return None


def save_blog(*, title, excerpt, content_html, author, image_path="", image_thumbnail="", blog_id=None):
    metadata = json.dumps(
        {
            "title": title,
            "slug": slugify(title),
            "excerpt": excerpt,
            "author": author,
            "image_path": image_path,
            "image_thumbnail": image_thumbnail,
        }
    )

    conn = get_conn()
    with conn.cursor() as cur:
        if blog_id:
            cur.execute(
                """
                UPDATE blogs
                SET blog_html = %s,
                    metadata = %s,
                    edited_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id
                """,
                (content_html, metadata, blog_id),
            )
        else:
            cur.execute(
                """
                INSERT INTO blogs (blog_html, metadata)
                VALUES (%s, %s)
                RETURNING id
                """,
                (content_html, metadata),
            )
        saved_id = cur.fetchone()["id"]

    conn.commit()
    return get_blog_by_id(saved_id)


def delete_blog(blog_id):
    conn = get_conn()
    with conn.cursor() as cur:
        for table in ["blog_views", "blog_likes", "blog_comments"]:
            cur.execute(f"DELETE FROM {table} WHERE blog_id = %s", (blog_id,))
        cur.execute("DELETE FROM blogs WHERE id = %s", (blog_id,))
    conn.commit()
