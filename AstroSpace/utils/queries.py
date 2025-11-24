import json
from AstroSpace.utils.phd2logparser import bokeh_phd2
from AstroSpace.utils.platesolve import get_overlays
from AstroSpace.utils.utils import  print_time

from AstroSpace.db import get_conn
from flask import current_app

#except software and cam_filter
DB_TABLES = [
        "camera",
        "telescope",
        "reducer",
        "guide_camera",
        "guider",
        "mount",
        "tripod",
        "filter_wheel",
        "eaf",
        "dew_heater",
        "flat_panel",
        "rotator"
    ]


def get_all_images(unique=False, limit=None):
    conn = get_conn()
    cur = conn.cursor()
    ilimit = ""
    if limit:
        ilimit = f"LIMIT {limit}"
    if unique:
        cur.execute(f"""
    SELECT * FROM (
    SELECT DISTINCT ON (title) id, title, slug, image_path, image_thumbnail, created_at
    FROM images
    ORDER BY title, created_at DESC
    {ilimit}
        ) t ORDER BY created_at DESC
""")
    else:
        cur.execute(
            "SELECT id, title, slug, image_path, image_thumbnail FROM images " \
            f"ORDER BY created_at DESC {ilimit}"
        )
    results = cur.fetchall()

    return results


def get_image_by_id(image_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM images WHERE id = {image_id}")
    row = cur.fetchone()
    if not row:
        return None
    return row

# Helper functions
def fetch_options(table):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT id, name FROM {table}")
    opts = cur.fetchall()
    cur.close()
    return opts

def get_image_tables(image_id, keep_original=False,bokeh_testing=False, testing=False):
    image = get_image_by_id(image_id)
    if not image:
        return "Image not found!, 404"
    conn = get_conn()
    equipment_list = []
    for table in DB_TABLES:
        if image[f"{table}_id"]:
            iid = image[f"{table}_id"]
            cur = conn.cursor()
            original_table = table
            if table == "guide_camera":
                table = "camera"
            cur.execute(f"SELECT * FROM {table} WHERE id = %s", (iid,))
            equipment = cur.fetchone()
            if equipment:
                equipment["table"] = original_table
                equipment_list.append(equipment)
            cur.close()

    # Get the dates
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM capture_dates WHERE image_id = %s ORDER BY capture_date",
        (image_id,),
    )
    dates = cur.fetchall()

    # calculate moon illumination
    if not keep_original:
        for d in dates:
            d["capture_date"] = d["capture_date"].strftime("%d %B %Y")

    # Get the subs
    cur.execute(f"SELECT * FROM image_lights WHERE image_id = {image_id}")
    lights = cur.fetchall()
    if not keep_original:
        for light in lights:
            light["temperature"] = f"{light['temperature']:.1f} °C"
            light["total_time"] = print_time(light["light_count"] * light["exposure_time"])
            light["exposure_time"] = f"{light['exposure_time']:.0f} sec"
            filter_name = light["cam_filter"]
            cur.execute(f"SELECT * FROM cam_filter WHERE name = '{filter_name}'")
            filter_row = cur.fetchone()
            if filter_row:
                light["filter_link"] = filter_row["link"]

    # Get the software
    cur.execute(f"SELECT * FROM image_software WHERE image_id = {image_id}")
    software = cur.fetchall()

    if not keep_original:
        software_list = []
        for s in software:
            cur.execute("SELECT * FROM software WHERE id = %s", (s["software_id"],))
            soft = cur.fetchone()
            if soft:
                software_list.append(soft)
    else:
        software_list = [s["id"] for s in software]
    cur.close()

    guiding_html, calibration_html, svg_image = "", "",""
    if not keep_original:
        # guide log plot
        if bokeh_testing:
            if image["guide_log"]:
                root_path = current_app.config['root_path']
                guiding_html, calibration_html = bokeh_phd2(image["guide_log"], root_path)
        else:
            guiding_html = image["guiding_html"]
            calibration_html = image["calibration_html"]

        # Get overlays
        if testing:
            if image["header_json"]:
                svg_image = get_overlays(image["header_json"])
        else:
            svg_image = json.loads(image["overlays_json"])

    
    return image, equipment_list, dates, lights, software_list, guiding_html, calibration_html,svg_image
