import json
import os

from psycopg2 import sql

from AstroSpace.constants import DB_TABLES, RELATED_MEDIA_VIDEO_EXTENSIONS
from AstroSpace.db import get_conn
from AstroSpace.utils.phd2logparser import deserialize_plot_payload
from AstroSpace.utils.platesolve import get_overlays
from AstroSpace.utils.utils import print_time


OPTION_TABLES = {*DB_TABLES, "software", "cam_filter"}


def _related_media_kind(path):
    extension = os.path.splitext(path or "")[1].lower().lstrip(".")
    return "video" if extension in RELATED_MEDIA_VIDEO_EXTENSIONS else "image"


def get_all_images(unique=False, limit=None):
    conn = get_conn()
    cur = conn.cursor()

    if unique:
        cur.execute(
            """
            SELECT id, title, short_description, slug, image_path, image_thumbnail, created_at
            FROM (
                SELECT DISTINCT ON (title)
                    id, title, short_description, slug, image_path, image_thumbnail, created_at
                FROM images
                ORDER BY title, created_at DESC
            ) t
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
    elif limit is not None:
        cur.execute(
            """
            SELECT id, title, short_description, slug, image_path, image_thumbnail, created_at
            FROM images
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
    else:
        cur.execute(
            """
            SELECT id, title, short_description, slug, image_path, image_thumbnail, created_at
            FROM images
            ORDER BY created_at DESC
            """
        )

    return cur.fetchall()


def _fetch_distinct_values(cur, query):
    cur.execute(query)
    return [row["value"] for row in cur.fetchall() if row.get("value") not in (None, "")]


def get_collection_filter_metadata():
    conn = get_conn()
    cur = conn.cursor()

    dropdowns = {
        "telescope_type": _fetch_distinct_values(
            cur,
            """
            SELECT DISTINCT t.type AS value
            FROM images i
            JOIN telescope t ON t.id = i.telescope_id
            WHERE t.type IS NOT NULL AND BTRIM(t.type) <> ''
            ORDER BY value
            """,
        ),
        "telescope_name": _fetch_distinct_values(
            cur,
            """
            SELECT DISTINCT t.name AS value
            FROM images i
            JOIN telescope t ON t.id = i.telescope_id
            WHERE t.name IS NOT NULL AND BTRIM(t.name) <> ''
            ORDER BY value
            """,
        ),
        "main_camera": _fetch_distinct_values(
            cur,
            """
            SELECT DISTINCT c.name AS value
            FROM images i
            JOIN camera c ON c.id = i.camera_id
            WHERE c.name IS NOT NULL AND BTRIM(c.name) <> ''
            ORDER BY value
            """,
        ),
        "guide_camera": _fetch_distinct_values(
            cur,
            """
            SELECT DISTINCT c.name AS value
            FROM images i
            JOIN camera c ON c.id = i.guide_camera_id
            WHERE c.name IS NOT NULL AND BTRIM(c.name) <> ''
            ORDER BY value
            """,
        ),
        "filter_type": _fetch_distinct_values(
            cur,
            """
            SELECT DISTINCT cf.type AS value
            FROM images i
            JOIN image_lights il ON il.image_id = i.id
            JOIN cam_filter cf ON cf.name = il.cam_filter
            WHERE cf.type IS NOT NULL AND BTRIM(cf.type) <> ''
            ORDER BY value
            """,
        ),
        "mount": _fetch_distinct_values(
            cur,
            """
            SELECT DISTINCT m.name AS value
            FROM images i
            JOIN mount m ON m.id = i.mount_id
            WHERE m.name IS NOT NULL AND BTRIM(m.name) <> ''
            ORDER BY value
            """,
        ),
        "object_type": _fetch_distinct_values(
            cur,
            """
            SELECT DISTINCT i.object_type AS value
            FROM images i
            WHERE i.object_type IS NOT NULL AND BTRIM(i.object_type) <> ''
            ORDER BY value
            """,
        ),
        "moon_phase": _fetch_distinct_values(
            cur,
            """
            SELECT DISTINCT cd.moon_phase AS value
            FROM capture_dates cd
            WHERE cd.moon_phase IS NOT NULL AND BTRIM(cd.moon_phase) <> ''
            ORDER BY value
            """,
        ),
        "author": _fetch_distinct_values(
            cur,
            """
            SELECT DISTINCT i.author AS value
            FROM images i
            WHERE i.author IS NOT NULL AND BTRIM(i.author) <> ''
            ORDER BY value
            """,
        ),
    }

    cur.execute(
        """
        SELECT
            MIN(t.focal_length) AS min_focal_length,
            MAX(t.focal_length) AS max_focal_length,
            MIN(i.pixel_scale) AS min_pixel_scale,
            MAX(i.pixel_scale) AS max_pixel_scale
        FROM images i
        LEFT JOIN telescope t ON t.id = i.telescope_id
        """
    )
    range_row = cur.fetchone() or {}

    cur.execute(
        """
        SELECT
            MIN(capture_date) AS min_capture_date,
            MAX(capture_date) AS max_capture_date
        FROM capture_dates
        """
    )
    capture_range_row = cur.fetchone() or {}

    cur.close()

    return {
        "dropdowns": dropdowns,
        "ranges": {
            "focal_length": {
                "min": range_row.get("min_focal_length"),
                "max": range_row.get("max_focal_length"),
            },
            "pixel_scale": {
                "min": range_row.get("min_pixel_scale"),
                "max": range_row.get("max_pixel_scale"),
            },
            "capture_dates": {
                "min": capture_range_row.get("min_capture_date"),
                "max": capture_range_row.get("max_capture_date"),
            },
        },
    }


def build_collection_query(filters):
    query = """
        SELECT id, title, short_description, slug, image_path, image_thumbnail, created_at
        FROM (
            SELECT DISTINCT ON (i.title)
                i.id,
                i.title,
                i.short_description,
                i.slug,
                i.image_path,
                i.image_thumbnail,
                i.created_at
            FROM images i
            LEFT JOIN telescope t ON t.id = i.telescope_id
            LEFT JOIN camera main_camera ON main_camera.id = i.camera_id
            LEFT JOIN camera guide_camera ON guide_camera.id = i.guide_camera_id
            LEFT JOIN mount m ON m.id = i.mount_id
            WHERE 1 = 1
    """

    conditions = []
    params = []

    if filters.get("telescope_type"):
        conditions.append("t.type = %s")
        params.append(filters["telescope_type"])

    if filters.get("telescope_name"):
        conditions.append("t.name = %s")
        params.append(filters["telescope_name"])

    if filters.get("main_camera"):
        conditions.append("main_camera.name = %s")
        params.append(filters["main_camera"])

    if filters.get("guide_camera"):
        conditions.append("guide_camera.name = %s")
        params.append(filters["guide_camera"])

    if filters.get("mount"):
        conditions.append("m.name = %s")
        params.append(filters["mount"])

    if filters.get("object_type"):
        conditions.append("i.object_type = %s")
        params.append(filters["object_type"])

    if filters.get("author"):
        conditions.append("i.author = %s")
        params.append(filters["author"])

    if filters.get("focal_length_min") is not None and filters.get("focal_length_max") is not None:
        conditions.append("t.focal_length BETWEEN %s AND %s")
        params.extend([filters["focal_length_min"], filters["focal_length_max"]])

    if filters.get("pixel_scale_min") is not None and filters.get("pixel_scale_max") is not None:
        conditions.append("i.pixel_scale BETWEEN %s AND %s")
        params.extend([filters["pixel_scale_min"], filters["pixel_scale_max"]])

    capture_conditions = []
    if filters.get("capture_date_start") is not None:
        capture_conditions.append("cd.capture_date >= %s")
        params.append(filters["capture_date_start"])
    if filters.get("capture_date_end") is not None:
        capture_conditions.append("cd.capture_date <= %s")
        params.append(filters["capture_date_end"])
    if filters.get("moon_phase"):
        capture_conditions.append("cd.moon_phase = %s")
        params.append(filters["moon_phase"])
    if capture_conditions:
        conditions.append(
            "EXISTS (SELECT 1 FROM capture_dates cd WHERE cd.image_id = i.id AND "
            + " AND ".join(capture_conditions)
            + ")"
        )

    if filters.get("filter_type"):
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM image_lights il
                JOIN cam_filter cf ON cf.name = il.cam_filter
                WHERE il.image_id = i.id AND cf.type = %s
            )
            """
        )
        params.append(filters["filter_type"])

    if conditions:
        query += "\n            AND " + "\n            AND ".join(conditions)

    query += """
            ORDER BY i.title, i.created_at DESC
        ) filtered_images
        ORDER BY created_at DESC
    """

    return query, params


def get_collection_images(filters):
    conn = get_conn()
    cur = conn.cursor()
    query, params = build_collection_query(filters)
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    return rows


def get_image_by_id(image_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM images WHERE id = %s", (image_id,))
    row = cur.fetchone()
    if not row:
        return None

    author = row.get("author")
    cur.execute(
        """
        SELECT display_image
        FROM users
        WHERE username = %s
        """,
        (author,),
    )
    user_row = cur.fetchone()
    if user_row:
        row["user_image"] = user_row["display_image"]

    return row


def fetch_options(table):
    if table not in OPTION_TABLES:
        raise ValueError(f"Unsupported options table: {table}")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        sql.SQL("SELECT id, name FROM {} ORDER BY name").format(sql.Identifier(table))
    )
    options = cur.fetchall()
    cur.close()
    return options


def get_image_tables(image_id, keep_original=False, testing=False):
    image = get_image_by_id(image_id)
    if not image:
        return "Image not found!, 404"

    conn = get_conn()
    equipment_list = []
    for table in DB_TABLES:
        if image[f"{table}_id"]:
            equipment_id = image[f"{table}_id"]
            cur = conn.cursor()
            original_table = table
            query_table = "camera" if table == "guide_camera" else table
            cur.execute(
                sql.SQL("SELECT * FROM {} WHERE id = %s").format(sql.Identifier(query_table)),
                (equipment_id,),
            )
            equipment = cur.fetchone()
            if equipment:
                equipment["table"] = original_table
                equipment_list.append(equipment)
            cur.close()

    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM capture_dates WHERE image_id = %s ORDER BY capture_date",
        (image_id,),
    )
    dates = cur.fetchall()

    if not keep_original:
        for capture_date in dates:
            capture_date["capture_date"] = capture_date["capture_date"].strftime("%d %B %Y")

    meta_json = image.get("meta_json", "{}") or "{}"
    meta_json = json.loads(meta_json)

    cur.execute("SELECT * FROM image_lights WHERE image_id = %s", (image_id,))
    lights = cur.fetchall()
    if not keep_original:
        weights = meta_json.get("variable", {})
        for light in lights:
            light["temperature"] = f"{light['temperature']:.1f} °C"
            if "WBPP weight 1" in weights:
                red = sum(map(float, weights.get("WBPP weight 1", [])))
                green = sum(map(float, weights.get("WBPP weight 2", [])))
                blue = sum(map(float, weights.get("WBPP weight 3", [])))
                light["effective_total"] = print_time((red + green + blue) * light["exposure_time"] / 3)
                light["effective_red"] = print_time(red * light["exposure_time"])
                light["effective_green"] = print_time(green * light["exposure_time"])
                light["effective_blue"] = print_time(blue * light["exposure_time"])

            light["total_time"] = print_time(light["light_count"] * light["exposure_time"])
            light["exposure_time"] = f"{light['exposure_time']:.0f} sec"
            cur.execute("SELECT * FROM cam_filter WHERE name = %s", (light["cam_filter"],))
            filter_row = cur.fetchone()
            if filter_row:
                light["filter_link"] = filter_row["link"]

    cur.execute("SELECT * FROM image_software WHERE image_id = %s", (image_id,))
    software = cur.fetchall()

    if not keep_original:
        software_list = []
        for software_row in software:
            cur.execute("SELECT * FROM software WHERE id = %s", (software_row["software_id"],))
            soft = cur.fetchone()
            if soft:
                software_list.append(soft)
    else:
        software_list = [software_row["software_id"] for software_row in software]

    cur.execute(
        """
        SELECT id, image_id, media_path, caption, sort_order, created_at
        FROM related_image_media
        WHERE image_id = %s
        ORDER BY sort_order ASC, id ASC
        """,
        (image_id,),
    )
    related_media = cur.fetchall()
    for media in related_media:
        media.pop("created_at", None)
        media["media_kind"] = _related_media_kind(media.get("media_path"))
        media["display_name"] = os.path.basename((media.get("media_path") or "").replace("\\", "/"))

    cur.close()

    guiding_plot, calibration_plot, svg_image = "", "", ""
    if not keep_original:
        guiding_plot = deserialize_plot_payload(image.get("guiding_plot_json"), "Guiding")
        calibration_plot = deserialize_plot_payload(image.get("calibration_plot_json"), "Calibration")

        if testing:
            if image["header_json"]:
                svg_image = get_overlays(image["header_json"])
        else:
            svg_image = json.loads(image["overlays_json"])

    return (
        image,
        equipment_list,
        dates,
        lights,
        software_list,
        guiding_plot,
        calibration_plot,
        svg_image,
        meta_json,
        related_media,
    )
