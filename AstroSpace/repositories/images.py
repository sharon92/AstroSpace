import json

from psycopg2 import sql

from AstroSpace.constants import DB_TABLES
from AstroSpace.db import get_conn
from AstroSpace.utils.phd2logparser import deserialize_plot_payload
from AstroSpace.utils.platesolve import get_overlays
from AstroSpace.utils.utils import print_time


OPTION_TABLES = {*DB_TABLES, "software", "cam_filter"}


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
    )
