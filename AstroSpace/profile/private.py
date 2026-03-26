# private profile - what the user can see and edit
import os
import logging
from flask import Blueprint, render_template, current_app, g, request, jsonify
from psycopg2 import sql
from psycopg2.extras import Json
from AstroSpace.constants import INVENTORY_TABLES, RELATED_MEDIA_VIDEO_EXTENSIONS
from AstroSpace.db import get_conn
from AstroSpace.auth import login_required
from AstroSpace.logging_utils import debug_log
from AstroSpace.services.authorization import current_user_is_admin, require_admin
from AstroSpace.services.content import sanitize_rich_text
from AstroSpace.services.uploads import allowed_file
from AstroSpace.utils.phd2logparser import build_plotly_payloads
from AstroSpace.utils.platesolve import rebuild_plate_solve_artifacts
from AstroSpace.utils.utils import (
    ALLOWED_IMG_EXTENSIONS,
    resize_image,
)
from werkzeug.utils import secure_filename

bp = Blueprint("private", __name__, url_prefix="/private")

INVENTORY_FIELD_CHOICES = {
    "telescope": {"type": ("refractor", "reflector", "catadioptric", "ritchey-chretien")},
    "mount": {"type": ("equatorial", "altazimuth")},
    "filter_wheel": {"type": ("manual", "motorized")},
    "rotator": {"type": ("manual", "motorized")},
    "software": {"type": ("acquisition", "processing")},
}
PURGE_UPLOAD_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    *{f".{extension}" for extension in RELATED_MEDIA_VIDEO_EXTENSIONS},
}


def normalize_inventory_values(table, values):
    normalized = dict(values)
    normalized["name"] = (normalized.get("name") or "").strip()
    if not normalized["name"]:
        raise ValueError("Name is required.")

    for field, allowed_values in INVENTORY_FIELD_CHOICES.get(table, {}).items():
        raw_value = normalized.get(field)
        if raw_value is None:
            continue

        value = raw_value.strip().lower() if isinstance(raw_value, str) else raw_value
        if value == "":
            normalized[field] = ""
            continue

        if value not in allowed_values:
            allowed = ", ".join(allowed_values)
            raise ValueError(f"{field} must be one of: {allowed}.")

        normalized[field] = value

    return normalized


def normalize_public_path(path):
    if not path:
        return ""
    return str(path).replace("\\", "/").strip().lstrip("/")


def resolve_upload_path(upload_root, public_path):
    normalized = normalize_public_path(public_path)
    if not normalized:
        return ""
    return os.path.normpath(os.path.join(upload_root, normalized.replace("/", os.sep)))


def collect_referenced_upload_paths(rows):
    referenced = set()
    for row in rows:
        for value in row:
            if not value:
                continue
            for item in str(value).split(","):
                normalized = normalize_public_path(item)
                if normalized:
                    referenced.add(normalized)
    return referenced


def collect_orphan_image_uploads(upload_root, referenced_paths):
    referenced = {normalize_public_path(path) for path in referenced_paths if path}
    orphans = []

    if not os.path.isdir(upload_root):
        return orphans

    for root, _, files in os.walk(upload_root):
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in PURGE_UPLOAD_EXTENSIONS:
                continue

            absolute_path = os.path.join(root, filename)
            relative_path = normalize_public_path(os.path.relpath(absolute_path, upload_root))
            if relative_path not in referenced:
                orphans.append(absolute_path)

    return sorted(orphans)


def rebuild_all_guiding_plots(db, upload_root):
    stats = {
        "updated": 0,
        "skipped": 0,
        "missing_files": [],
        "errors": [],
    }

    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, guide_log
            FROM images
            WHERE guide_log IS NOT NULL AND NULLIF(BTRIM(guide_log), '') IS NOT NULL
            ORDER BY id
            """
        )
        rows = cur.fetchall()

    for row in rows:
        image_id = row["id"]
        relative_logs = [normalize_public_path(path) for path in row["guide_log"].split(",") if normalize_public_path(path)]
        absolute_logs = [resolve_upload_path(upload_root, path) for path in relative_logs]
        missing = [path for path, absolute in zip(relative_logs, absolute_logs) if not os.path.exists(absolute)]

        if missing:
            stats["skipped"] += 1
            stats["missing_files"].append({"image_id": image_id, "paths": missing})
            continue

        try:
            guiding_plot, calibration_plot = build_plotly_payloads(",".join(absolute_logs))
            with db.cursor() as cur:
                cur.execute(
                    """
                    UPDATE images
                    SET guiding_plot_json = %s,
                        calibration_plot_json = %s,
                        edited_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (Json(guiding_plot), Json(calibration_plot), image_id),
                )
            db.commit()
            stats["updated"] += 1
        except Exception as exc:
            db.rollback()
            stats["skipped"] += 1
            stats["errors"].append({"image_id": image_id, "error": str(exc)})
    return stats


def rebuild_all_plate_solves(db, upload_root):
    stats = {
        "updated": 0,
        "skipped": 0,
        "missing_files": [],
        "errors": [],
    }

    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, image_path, header_json
            FROM images
            WHERE image_path IS NOT NULL AND NULLIF(BTRIM(image_path), '') IS NOT NULL
              AND header_json IS NOT NULL AND NULLIF(BTRIM(header_json), '') IS NOT NULL
            ORDER BY id
            """
        )
        rows = cur.fetchall()

    current_app.logger.info("Starting plate-solve rebuild for %s images", len(rows))

    for row in rows:
        image_id = row["id"]
        public_image_path = normalize_public_path(row["image_path"])
        absolute_image_path = resolve_upload_path(upload_root, public_image_path)

        if not os.path.exists(absolute_image_path):
            stats["skipped"] += 1
            stats["missing_files"].append({"image_id": image_id, "path": public_image_path})
            current_app.logger.warning(
                "Skipping plate-solve rebuild for image_id=%s because image file is missing: %s",
                image_id,
                public_image_path,
            )
            continue

        try:
            thumbnail_path, pixel_scale, overlays_json, header_json = rebuild_plate_solve_artifacts(
                absolute_image_path,
                public_image_path,
                row["header_json"],
            )
            with db.cursor() as cur:
                cur.execute(
                    """
                    UPDATE images
                    SET image_thumbnail = %s,
                        pixel_scale = %s,
                        overlays_json = %s,
                        header_json = %s,
                        edited_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (thumbnail_path, pixel_scale, overlays_json, header_json, image_id),
                )
            db.commit()
            stats["updated"] += 1
            debug_log(
                "Rebuilt plate-solve artifacts for image_id=%s thumbnail=%s pixel_scale=%s",
                image_id,
                thumbnail_path,
                pixel_scale,
            )
        except Exception as exc:
            db.rollback()
            stats["skipped"] += 1
            stats["errors"].append({"image_id": image_id, "error": str(exc)})
            current_app.logger.warning(
                "Skipping plate-solve rebuild for image_id=%s because artifact rebuild failed: %s",
                image_id,
                exc,
            )

    current_app.logger.info(
        "Plate-solve rebuild finished (updated=%s, skipped=%s)",
        stats["updated"],
        stats["skipped"],
    )
    return stats


def purge_unbound_image_uploads(db, upload_root):
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT image_path, image_thumbnail, starless_image_path
            FROM images
            """
        )
        image_rows = cur.fetchall()
        cur.execute(
            """
            SELECT media_path
            FROM related_image_media
            WHERE media_path IS NOT NULL AND NULLIF(BTRIM(media_path), '') IS NOT NULL
            """
        )
        related_media_rows = cur.fetchall()
        cur.execute(
            """
            SELECT display_image
            FROM users
            WHERE display_image IS NOT NULL AND NULLIF(BTRIM(display_image), '') IS NOT NULL
            """
        )
        user_rows = cur.fetchall()

    referenced = collect_referenced_upload_paths(
        [
            (
                row.get("image_path"),
                row.get("image_thumbnail"),
                row.get("starless_image_path"),
            )
            for row in image_rows
        ]
        + [(row.get("media_path"),) for row in related_media_rows]
        + [(row.get("display_image"),) for row in user_rows]
    )
    orphans = collect_orphan_image_uploads(upload_root, referenced)

    deleted = []
    errors = []
    for absolute_path in orphans:
        try:
            os.remove(absolute_path)
            deleted.append(absolute_path)
        except OSError as exc:
            errors.append({"path": absolute_path, "error": str(exc)})

    return {
        "deleted": len(deleted),
        "errors": errors,
        "deleted_paths": [normalize_public_path(os.path.relpath(path, upload_root)) for path in deleted],
    }

@bp.route("/profile")
@login_required
def profile():

    tabs = ["Posts", "Inventory", "Settings"]
    active_tab = request.args.get("tab")
    if active_tab not in tabs:
        active_tab = tabs[0]

    db = get_conn()
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, title, short_description, image_thumbnail, slug, pixel_scale, object_type, location, created_at FROM images WHERE author = %s ORDER BY created_at DESC",
            (g.user["username"],),
        )
        posts = cur.fetchall()

    with db.cursor() as cur:
        cur.execute(
            """
            select * from users
            WHERE id = %s
            """,
            (g.user["id"],),
        )
        settings = cur.fetchone()

    try:
        with db.cursor() as cur:
            cur.execute(
                """
                select * from web_info
                """,
            )
            web_info = cur.fetchone()
    except Exception:
        debug_log(
            "Failed to load web_info for profile page; continuing with defaults.",
            level=logging.WARNING,
            exc_info=True,
        )
        web_info = {}

    inventory_dict = {}
    data_types = {}
    with db.cursor() as cur:
        for item in INVENTORY_TABLES:
            inventory_dict[item] = {}
            data_types[item] = {}
            
            # Pull schema info for defaults
            cur.execute("""
                SELECT column_name, data_type, column_default
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (item,))
            columns = cur.fetchall()

            # Create default/empty row
            default_obj = {}
            data_type = {}
            for col in columns:
                colname = col["column_name"]
                data_type[colname] = coltype = col["data_type"]
                data_types[item][colname] = coltype
                coldefault = col["column_default"]

                # decide default value
                if coldefault is not None:
                     default_obj[colname] = coldefault
                elif coltype in ("integer", "bigint", "smallint", "numeric", "double precision", "real"):
                    default_obj[colname] = 0
                elif coltype in ("boolean",):
                    default_obj[colname] = False
                else:
                    default_obj[colname] = ""      # text/varchar/default case
                default_obj["id"] = -1  # Indicate new item

            # Add to inventory_dict
            inventory_dict[item]["➕ Add New"] = default_obj

            cur.execute(sql.SQL("SELECT * FROM {}").format(sql.Identifier(item)))
            values = cur.fetchall()

            for obj in values:
                inventory_dict[item][obj["name"]] = obj

    return render_template(
        "profile.html",
        posts=posts,
        inventory=inventory_dict,
        user_settings=settings,
        tabs=tabs,
        data_type=data_types,
        inventory_constraints=INVENTORY_FIELD_CHOICES,
        WebName=current_app.config["TITLE"],
        web_info = web_info,
        can_manage_site=current_user_is_admin(),
        active_tab=active_tab,
    )

@bp.route("/update_inventory", methods=["POST"])
@login_required
def update_inventory():
    require_admin()
    data = request.get_json()
    table = data.get("type")
    values = dict(data.get("values") or {})
    if table not in INVENTORY_TABLES:
        debug_log("Rejected unsupported inventory type=%s", table, level=logging.WARNING)
        return jsonify({"message": "Unsupported inventory type"}), 400
    tid = values.pop("id", None)
    operation = "insert" if tid == -1 else "update"
    debug_log(
        "Inventory %s requested by user=%s for table=%s",
        operation,
        g.user["username"],
        table,
    )

    try:
        values = normalize_inventory_values(table, values)
    except ValueError as exc:
        debug_log(
            "Inventory validation failed for table=%s: %s",
            table,
            exc,
            level=logging.WARNING,
        )
        return jsonify({"message": str(exc)}), 400

    name = values["name"]
    columns = list(values.keys())
    column_identifiers = sql.SQL(", ").join(sql.Identifier(column) for column in columns)
    placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in columns)
    
    db = get_conn()
    
    try:
        if tid == -1:
            query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING id").format(
                sql.Identifier(table),
                column_identifiers,
                placeholders,
            )
           
            with db.cursor() as cur:
                cur.execute(
                    query,
                    tuple(values.values()),
                )
                new_id = cur.fetchone()["id"]
                debug_log(
                    "Inserted inventory row table=%s id=%s name=%s",
                    table,
                    new_id,
                    name,
                )

        else:
            set_clause = sql.SQL(", ").join(
                sql.SQL("{} = %s").format(sql.Identifier(column)) for column in columns
            )
            query = sql.SQL(
                """
                UPDATE {}
                SET {}
                WHERE id = %s
                """
            ).format(sql.Identifier(table), set_clause)

            with db.cursor() as cur:
                cur.execute(
                    query,
                    (
                        *tuple(values.values()),
                        tid
                    ),
                )
                debug_log(
                    "Updated inventory row table=%s id=%s name=%s",
                    table,
                    tid,
                    name,
                )
        
        db.commit()
    except Exception as exc:
        db.rollback()
        current_app.logger.exception(
            "Failed to update inventory table=%s operation=%s name=%s",
            table,
            operation,
            name,
        )
        return jsonify({"message": str(exc)}), 400

    debug_log(
        "Inventory %s committed successfully for table=%s name=%s",
        operation,
        table,
        name,
        level=logging.INFO,
    )
    return jsonify({"message": "Inventory updated successfully"}), 200


@bp.route("/admin/redo_guiding_graphs", methods=["POST"])
@login_required
def redo_guiding_graphs():
    require_admin()
    db = get_conn()

    try:
        stats = rebuild_all_guiding_plots(db, current_app.config["UPLOAD_PATH"])
    except Exception as exc:
        db.rollback()
        current_app.logger.exception("Failed to rebuild guiding plots")
        return jsonify({"message": f"Failed to rebuild guiding plots: {exc}"}), 500

    message = f"Updated {stats['updated']} images."
    if stats["skipped"]:
        message += f" Skipped {stats['skipped']} images."

    return jsonify(
        {
            "message": message,
            "stats": stats,
        }
    ), 200


@bp.route("/admin/redo_plate_solving", methods=["POST"])
@login_required
def redo_plate_solving():
    require_admin()
    db = get_conn()
    current_app.logger.info(
        "Admin user=%s requested plate-solve rebuild for all images",
        g.user["username"],
    )

    try:
        stats = rebuild_all_plate_solves(db, current_app.config["UPLOAD_PATH"])
    except Exception as exc:
        db.rollback()
        current_app.logger.exception("Failed to rebuild plate-solving artifacts")
        return jsonify({"message": f"Failed to rebuild plate-solving artifacts: {exc}"}), 500

    message = f"Updated {stats['updated']} images."
    if stats["skipped"]:
        message += f" Skipped {stats['skipped']} images."

    return jsonify(
        {
            "message": message,
            "stats": stats,
        }
    ), 200


@bp.route("/admin/purge_orphan_image_uploads", methods=["POST"])
@login_required
def purge_orphan_image_uploads():
    require_admin()
    db = get_conn()

    try:
        stats = purge_unbound_image_uploads(db, current_app.config["UPLOAD_PATH"])
    except Exception as exc:
        current_app.logger.exception("Failed to purge unbound image uploads")
        return jsonify({"message": f"Failed to purge unbound images/thumbnails: {exc}"}), 500

    message = f"Deleted {stats['deleted']} unbound images/thumbnails."
    if stats["errors"]:
        message += f" {len(stats['errors'])} deletions failed."

    return jsonify(
        {
            "message": message,
            "stats": stats,
        }
    ), 200

@bp.route("/update_settings", methods=["POST"])
@login_required
def update_settings():
    db = get_conn()

    user = g.user["username"]
    user_id = str(g.user["id"])
    debug_log(
        "Updating profile settings for user=%s user_id=%s",
        user,
        user_id,
        level=logging.INFO,
    )

    # Get form values
    display_name = request.form.get("display_name")
    bio = request.form.get("bio")
    astrometry_api_key = request.form.get("astrometry_api")
    open_weather_api_key = request.form.get("owm_api")
    telescopius_api_key = request.form.get("telescopius_api")

    bio = sanitize_rich_text(bio)

    display_image = request.files.get("display_image")
    filename_to_store = ""

    # ---- Image Upload ----
    if display_image and display_image.filename and allowed_file(display_image.filename, ALLOWED_IMG_EXTENSIONS):

        user_dir = os.path.join(current_app.config["UPLOAD_PATH"], user_id)
        os.makedirs(user_dir, exist_ok=True)
        
        filename = secure_filename(display_image.filename)
        final_name = f"{user}_{filename}"
        image_path = os.path.join(user_dir, final_name)

        try:
            display_image.save(image_path)
        
            path, ext = os.path.splitext(image_path)
            thumbnail_path = path + "_thumbnail.jpg"
            resize_image(image_path, thumbnail_path)

            thumbnail_name = os.path.basename(thumbnail_path)
            filename_to_store = f"{user_id}/{thumbnail_name}"
        except Exception as e:
            debug_log(
                "Display image save failed for user_id=%s",
                user_id,
                level=logging.WARNING,
                exc_info=True,
            )

    # ---- Update user row ----
    debug_log("Updating users table for user_id=%s", user_id)
    try:
        with db.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET display_name = %s,
                    bio = %s,
                    astrometry_api_key = %s,
                    open_weather_api_key = %s,
                    telescopius_api_key = %s
                WHERE id = %s
                """,
                (display_name, bio, astrometry_api_key, open_weather_api_key, telescopius_api_key, user_id),
            )
            if filename_to_store:
                cur.execute(
                    """
                    UPDATE users
                    SET display_image = %s
                    WHERE id = %s
                    """,
                    (filename_to_store, user_id),
                )
        db.commit()
        debug_log("User settings committed for user_id=%s", user_id, level=logging.INFO)
    except Exception as e:
        debug_log(
            "User settings update failed for user_id=%s",
            user_id,
            level=logging.WARNING,
            exc_info=True,
        )

    # ---- WEB INFO ----
    welcome_note = request.form.get("welcome_note")
    welcome_note = sanitize_rich_text(welcome_note)

    site_name = request.form.get("site_name")

    if current_user_is_admin():
        debug_log("Updating web_info content for admin user_id=%s", user_id)

        try:
            with db.cursor() as cur:
                cur.execute("SELECT id FROM web_info LIMIT 1")
                row = cur.fetchone()

                if row:
                    cur.execute("""
                        UPDATE web_info
                        SET welcome_message = %s,
                                site_name = %s
                        WHERE id = %s
                    """, (welcome_note, site_name, row["id"]))
                else:
                    cur.execute("""
                        INSERT INTO web_info (welcome_message, site_name)
                        VALUES (%s, %s)
                    """, (welcome_note, site_name))

            db.commit()
            debug_log("web_info content committed successfully", level=logging.INFO)

        except Exception as e:
            debug_log(
                "web_info content update failed",
                level=logging.WARNING,
                exc_info=True,
            )

    return jsonify({"status": "ok"})
