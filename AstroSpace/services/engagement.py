import hmac
import ipaddress
import secrets
from dataclasses import dataclass
from hashlib import sha256

from flask import current_app, request

from AstroSpace.db import get_conn
from AstroSpace.services.cookies import (
    COMMENTER_COOKIE_MAX_AGE,
    COMMENTER_NAME_COOKIE_NAME,
    PREFERENCE_COOKIE_MAX_AGE,
    VISITOR_COOKIE_MAX_AGE,
    VISITOR_COOKIE_NAME,
    clear_response_cookie,
    consent_allows,
    set_response_cookie,
)


COMMENT_COOLDOWN_SECONDS = 60
COMMENT_BURST_LIMIT = 5
COMMENT_BURST_WINDOW_MINUTES = 15
COMMENT_TEXT_LIMIT = 1500
COMMENT_NAME_LIMIT = 40
COMMENT_THREAD_LIMIT = 100


class EngagementError(ValueError):
    status_code = 400


class CommentRateLimitError(EngagementError):
    status_code = 429


@dataclass
class VisitorIdentity:
    visitor_hash: str
    visitor_source: str
    ip_hash: str | None
    user_agent_hash: str | None
    visitor_cookie_hash: str | None
    visitor_cookie_value: str | None
    new_visitor_cookie: str | None


def _hash_secret():
    return str(
        current_app.config.get("VISITOR_HASH_SECRET")
        or current_app.config.get("SECRET_KEY")
        or "astrospace-visitor"
    ).encode("utf-8")


def _hash_value(value):
    return hmac.new(_hash_secret(), str(value).encode("utf-8"), sha256).hexdigest()


def _client_ip(request_like=None):
    request_like = request_like or request
    forwarded_for = request_like.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return (request_like.headers.get("X-Real-IP") or request_like.remote_addr or "").strip()


def _normalize_ip(ip_value):
    if not ip_value:
        return "unknown"

    try:
        parsed_ip = ipaddress.ip_address(ip_value)
    except ValueError:
        return ip_value[:64]

    if parsed_ip.version == 4:
        network = ipaddress.ip_network(f"{parsed_ip.exploded}/24", strict=False)
        return f"{network.network_address}/24"

    network = ipaddress.ip_network(f"{parsed_ip.exploded}/56", strict=False)
    return f"{network.network_address}/56"


def _normalize_user_agent(request_like=None):
    request_like = request_like or request
    user_agent = request_like.user_agent
    browser = user_agent.browser or "unknown"
    version = user_agent.version or "0"
    platform = user_agent.platform or "unknown"
    language = request_like.headers.get("Accept-Language", "").split(",")[0].strip()[:32]
    return "|".join((browser, version, platform, language))


def build_visitor_identity(request_like=None):
    request_like = request_like or request
    community_allowed = consent_allows("community", request_like)

    normalized_ip = _normalize_ip(_client_ip(request_like))
    normalized_user_agent = _normalize_user_agent(request_like)
    ip_hash = _hash_value(f"ip:{normalized_ip}")
    user_agent_hash = _hash_value(f"ua:{normalized_user_agent}")

    visitor_cookie_value = None
    visitor_cookie_hash = None
    new_visitor_cookie = None

    if community_allowed:
        visitor_cookie_value = request_like.cookies.get(VISITOR_COOKIE_NAME)
        if not visitor_cookie_value:
            visitor_cookie_value = secrets.token_urlsafe(24)
            new_visitor_cookie = visitor_cookie_value
        visitor_cookie_hash = _hash_value(f"visitor:{visitor_cookie_value}")
        visitor_hash = visitor_cookie_hash
        visitor_source = "cookie"
    else:
        visitor_hash = _hash_value(f"network:{normalized_ip}|{normalized_user_agent}")
        visitor_source = "network"

    return VisitorIdentity(
        visitor_hash=visitor_hash,
        visitor_source=visitor_source,
        ip_hash=ip_hash,
        user_agent_hash=user_agent_hash,
        visitor_cookie_hash=visitor_cookie_hash,
        visitor_cookie_value=visitor_cookie_value,
        new_visitor_cookie=new_visitor_cookie,
    )


def apply_visitor_cookie(response, visitor_identity):
    if visitor_identity.new_visitor_cookie:
        set_response_cookie(
            response,
            VISITOR_COOKIE_NAME,
            visitor_identity.new_visitor_cookie,
            VISITOR_COOKIE_MAX_AGE,
            httponly=False,
        )


def apply_commenter_cookie(response, display_name):
    if consent_allows("preferences"):
        set_response_cookie(
            response,
            COMMENTER_NAME_COOKIE_NAME,
            display_name,
            COMMENTER_COOKIE_MAX_AGE,
            httponly=False,
        )
    else:
        clear_response_cookie(response, COMMENTER_NAME_COOKIE_NAME)


def clear_commenter_cookie(response):
    clear_response_cookie(response, COMMENTER_NAME_COOKIE_NAME)


def commenter_name_from_request(request_like=None):
    request_like = request_like or request
    if not consent_allows("preferences", request_like):
        return ""
    return (request_like.cookies.get(COMMENTER_NAME_COOKIE_NAME) or "").strip()


def record_image_view(image_id, visitor_identity):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO image_views (
                image_id,
                user_id,
                visitor_hash,
                visitor_source,
                ip_hash,
                user_agent_hash,
                visitor_cookie_hash,
                viewed_at,
                last_seen_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (image_id, visitor_hash)
            DO UPDATE SET
                last_seen_at = CURRENT_TIMESTAMP,
                visitor_source = EXCLUDED.visitor_source,
                ip_hash = COALESCE(EXCLUDED.ip_hash, image_views.ip_hash),
                user_agent_hash = COALESCE(EXCLUDED.user_agent_hash, image_views.user_agent_hash),
                visitor_cookie_hash = COALESCE(EXCLUDED.visitor_cookie_hash, image_views.visitor_cookie_hash)
            """,
            (
                image_id,
                visitor_identity.visitor_hash,
                visitor_identity.visitor_hash,
                visitor_identity.visitor_source,
                visitor_identity.ip_hash,
                visitor_identity.user_agent_hash,
                visitor_identity.visitor_cookie_hash,
            ),
        )
    conn.commit()


def fetch_image_engagement_state(image_id, visitor_identity, include_comments=True):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM image_views WHERE image_id = %s) AS view_count,
                (SELECT COUNT(*) FROM image_likes WHERE image_id = %s) AS like_count,
                (SELECT COUNT(*) FROM image_comments WHERE image_id = %s AND status = 'published') AS comment_count,
                EXISTS(
                    SELECT 1
                    FROM image_likes
                    WHERE image_id = %s
                      AND visitor_hash = %s
                ) AS liked
            """,
            (
                image_id,
                image_id,
                image_id,
                image_id,
                visitor_identity.visitor_hash,
            ),
        )
        summary = cur.fetchone() or {}

        comments = []
        if include_comments:
            cur.execute(
                """
                SELECT id, commented_by, comment, commented_at
                FROM image_comments
                WHERE image_id = %s
                  AND status = 'published'
                ORDER BY commented_at ASC
                LIMIT %s
                """,
                (image_id, COMMENT_THREAD_LIMIT),
            )
            comments = cur.fetchall()

    return {
        "view_count": int(summary.get("view_count") or 0),
        "like_count": int(summary.get("like_count") or 0),
        "comment_count": int(summary.get("comment_count") or 0),
        "liked": bool(summary.get("liked")),
        "comments": comments,
    }


def like_image(image_id, visitor_identity):
    conn = get_conn()
    liked = False
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM image_likes
            WHERE image_id = %s
              AND visitor_hash = %s
            RETURNING id
            """,
            (image_id, visitor_identity.visitor_hash),
        )
        removed = cur.fetchone() is not None
        if not removed:
            cur.execute(
                """
                INSERT INTO image_likes (
                    image_id,
                    user_id,
                    visitor_hash,
                    visitor_source,
                    ip_hash,
                    user_agent_hash,
                    visitor_cookie_hash,
                    liked_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (image_id, visitor_hash) DO NOTHING
                RETURNING id
                """,
                (
                    image_id,
                    visitor_identity.visitor_hash,
                    visitor_identity.visitor_hash,
                    visitor_identity.visitor_source,
                    visitor_identity.ip_hash,
                    visitor_identity.user_agent_hash,
                    visitor_identity.visitor_cookie_hash,
                ),
            )
            liked = cur.fetchone() is not None
    conn.commit()
    return liked


def submit_image_comment(image_id, visitor_identity, display_name, comment):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT commented_at
            FROM image_comments
            WHERE visitor_hash = %s
            ORDER BY commented_at DESC
            LIMIT 1
            """,
            (visitor_identity.visitor_hash,),
        )
        last_comment = cur.fetchone()
        if last_comment:
            cur.execute(
                """
                SELECT EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - %s)) AS elapsed_seconds
                """,
                (last_comment["commented_at"],),
            )
            elapsed_row = cur.fetchone() or {}
            if (elapsed_row.get("elapsed_seconds") or 0) < COMMENT_COOLDOWN_SECONDS:
                raise CommentRateLimitError(
                    f"Please wait {COMMENT_COOLDOWN_SECONDS} seconds before posting another comment."
                )

        cur.execute(
            f"""
            SELECT COUNT(*) AS burst_count
            FROM image_comments
            WHERE visitor_hash = %s
              AND commented_at >= (CURRENT_TIMESTAMP - INTERVAL '{COMMENT_BURST_WINDOW_MINUTES} minutes')
            """,
            (visitor_identity.visitor_hash,),
        )
        burst_row = cur.fetchone() or {}
        if int(burst_row.get("burst_count") or 0) >= COMMENT_BURST_LIMIT:
            raise CommentRateLimitError(
                "You have reached the temporary comment limit. Please try again in a few minutes."
            )

        cur.execute(
            """
            INSERT INTO image_comments (
                image_id,
                ip_address,
                comment,
                commented_at,
                commented_by,
                visitor_hash,
                visitor_source,
                ip_hash,
                user_agent_hash,
                visitor_cookie_hash,
                status
            )
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s, %s, %s, %s, %s, %s, 'published')
            RETURNING id, commented_at
            """,
            (
                image_id,
                visitor_identity.ip_hash,
                comment,
                display_name,
                visitor_identity.visitor_hash,
                visitor_identity.visitor_source,
                visitor_identity.ip_hash,
                visitor_identity.user_agent_hash,
                visitor_identity.visitor_cookie_hash,
            ),
        )
        inserted = cur.fetchone()
    conn.commit()
    return inserted
