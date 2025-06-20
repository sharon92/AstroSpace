import os
import requests
import json
from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, current_app, g, send_from_directory
)
# from werkzeug.exceptions import abort
from astroquery.simbad import Simbad
from datetime import datetime

from AstroSpace.auth import login_required
from AstroSpace.db import get_conn
from AstroSpace.utils.moon_phase import get_moon_illumination
from AstroSpace.utils.phd2logparser import bokeh_phd2
from AstroSpace.utils.platesolve import platesolve
from AstroSpace.utils.queries import get_image_tables, get_all_images, get_image_by_id, fetch_options
from AstroSpace.utils.utils import  geocode,slugify
from werkzeug.utils import secure_filename

bp = Blueprint('blog', __name__)

ALLOWED_IMG_EXTENSIONS = { 'jpg', 'jpeg'}
ALLOWED_TXT_EXTENSIONS = { 'txt' }


@bp.route('/uploads/<path:filename>')
def upload(filename):
    return send_from_directory(current_app.config["UPLOAD_PATH"], filename)

# List view
@bp.route("/")
@bp.route("/home")
def home():
    top_images = get_all_images(unique=True, limit=10)
    return render_template("home.html", WebName = current_app.config["TITLE"], top_images=top_images)

@bp.route("/collection")
def collection():
    images = get_all_images(unique=True)
    return render_template("collection.html", images=images, WebName = current_app.config["TITLE"])

@bp.route("/get_elevation")
def get_elevation():
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    url = f"https://api.opentopodata.org/v1/test-dataset?locations={lat},{lon}"
    r = requests.get(url)
    if r.status_code == 200:
        return str(round(r.json()["results"][0]["elevation"]))
    else:
        return "0"
    
@bp.route("/blog")
@login_required
def new_blog():
    return "Not yet Implemented"

@bp.route("/equipment")
@login_required
def add_equipment():
    return "Not yet Implemented"

@bp.route("/image/<int:image_id>/<string:image_name>")
def image_detail(image_id, image_name):
    tables = get_image_tables(image_id)
    if len(tables) == 1:
        return tables
    background_image = tables[0]["image_path"]
    table_names = ["image", "equipment_list", "dates", "lights", "software_list", "guiding_html", "calibration_html","svg_image"]
    # image, equipment_list, dates, lights, software_list, guiding_html, calibration_html,svg_image = tables
    images = [dict(zip(table_names,tables))]


    db = get_conn()
    with db.cursor() as cur:
        cur.execute("SELECT id FROM images WHERE slug = %s ORDER BY created_at DESC", (image_name,))
        prev_images = cur.fetchall()

    for i in prev_images:
        if i["id"] != image_id:
            images += [dict(zip(table_names,get_image_tables(i["id"])))]


    return render_template(
        "image_detail.html",
        background_image=background_image,
        images=images, WebName = current_app.config["TITLE"]
    )

# List view
@bp.route("/posts")
@login_required
def list_images():
    db = get_conn()
    with db.cursor() as cur:
        cur.execute("SELECT id, title, created_at FROM images WHERE author = %s ORDER BY created_at DESC",
        (g.user["username"],))
        posts = cur.fetchall()
    
    return render_template("user_posts.html", posts=posts, WebName = current_app.config["TITLE"])


# New post form
def render_image_form(title, **kwargs):
    cameras = fetch_options("camera")
    telescopes = fetch_options("telescope")
    reducer = fetch_options("reducer")
    mount = fetch_options("mount")
    tripod = fetch_options("tripod")
    filter_wheel = fetch_options("filter_wheel")
    eaf = fetch_options("eaf")
    dew_heater = fetch_options("dew_heater")
    flat_panel = fetch_options("flat_panel")
    oag = fetch_options("off_axis_guider")

    softwares = fetch_options("software")
    filters = fetch_options("filter")
    filter_options = "".join(
        [f'<option value="{f["name"]}">{f["name"]}</option>' for f in filters]
    )

    option_none = '<option value="0">None</option>'

    return render_template(
        "create.html", WebName = current_app.config["TITLE"],
        title=title,
        cameras=cameras,
        telescopes=telescopes,
        reducer=reducer,
        mount=mount,
        tripod=tripod,
        filter_wheel=filter_wheel,
        eaf=eaf,
        dew_heater=dew_heater,
        flat_panel=flat_panel,
        oag=oag,
        softwares=softwares,
        filter_options=filter_options,
        option_none=option_none,
        **kwargs
    )

@bp.route("/new")
@login_required
def new_image():
    return render_image_form("New Post",  equipment={}, capture_dates=[], software_list=[], lights_json=json.dumps([]), is_edit=False)

@bp.route("/edit/<int:image_id>")
@login_required
def edit_image(image_id):
    tables = get_image_tables(image_id, keep_original=True)
    if len(tables) == 1:
        return tables
    
    image, equipment_list, dates, lights, software_list, _,_,_ = tables

    capture_dates = [d["capture_date"].strftime("%Y-%m-%d") for d in dates] 
    
    equipment = {}
    for eq in equipment_list:
        equipment[eq["table"]] = eq["id"]

    return render_image_form("Edit Post", image=image, equipment=equipment, capture_dates=capture_dates, software_list = software_list, lights_json =json.dumps(lights),  is_edit=True)


@bp.route("/delete")
@login_required
def delete_image(img_id):
    conn = get_conn()
    cur = conn.cursor()
    # Clear and reinsert related tables
    cur.execute("DELETE FROM images WHERE id = %s", (img_id,))
    cur.execute("DELETE FROM image_views WHERE image_id = %s", (img_id,))
    cur.execute("DELETE FROM image_likes WHERE image_id = %s", (img_id,))
    cur.execute("DELETE FROM image_comments WHERE image_id = %s", (img_id,)) 
    cur.execute("DELETE FROM capture_dates WHERE image_id = %s", (img_id,))
    cur.execute("DELETE FROM image_lights WHERE image_id = %s", (img_id,))
    cur.execute("DELETE FROM image_software WHERE image_id = %s", (img_id,)) 
    conn.commit()
    cur.close()
    flash("Post deleted successfully!")
    return redirect(url_for("blog.list_images"))

def allowed_file(filename, allowed_extensions=ALLOWED_IMG_EXTENSIONS):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

@bp.route("/create", methods=["POST"])
@login_required
def save_image():
    user = g.user["username"]
    user_id = str(g.user["id"])

    os.makedirs(os.path.join(current_app.config["UPLOAD_PATH"], user_id), exist_ok=True)

    form = request.form
    img_id = form.get("image_id")
    if img_id:
        tmp_img = get_image_by_id(img_id)

    lat = form.get("location_latitude") or None
    lon = form.get("location_longitude") or None
    if not lat or not lon:
        lat, lon = geocode(form["location"])

    title = form.get("title")
    Simbad.add_votable_fields("otype_txt")
    query = Simbad.query_object(title)
    object_type = "Unknown"
    if query and len(query) > 0:
        title = query[0]["main_id"].replace("NAME", "").strip()
        object_type = query[0]["otype_txt"]

    file = request.files.get("image_path")
    if file.filename and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        image_path = os.path.join(current_app.config["UPLOAD_PATH"], user_id, filename)
        img_path_upload = f"{user_id}/{filename}"
        file.save(image_path)
        header_json, svg_image, thumbnail_path = platesolve(image_path,user_id)
    elif img_id:
        img_path_upload = form.get("prev_img")
        if form.get("redo_plate_solve") == "on":
            full_img_path = os.path.join(current_app.config["UPLOAD_PATH"], img_path_upload.replace("/","\\"))
            header_json, svg_image, thumbnail_path = platesolve(full_img_path,user_id)
        else:
            header_json = tmp_img["header_json"]   
            svg_image = tmp_img["overlays_json"]
            thumbnail_path = tmp_img["image_thumbnail"]

    guide_logs = request.files.getlist('guide_logs')
    new_guide_logs = any(i.filename for i in guide_logs)
    if new_guide_logs:
        print("Generating guide log plot...")
        iguide_logs = []   
        iguide_logs_upload = []     
        for file in guide_logs:
            if file and allowed_file(file.filename, ALLOWED_TXT_EXTENSIONS):
                filename = secure_filename(file.filename)
                guide_log_path = os.path.join(current_app.config["UPLOAD_PATH"], user_id, filename)
                file.save(guide_log_path)
                iguide_logs.append(guide_log_path)
                iguide_logs_upload.append(f"{user_id}/{filename}")
        guide_logs = ','.join(iguide_logs)
        guiding_html,calibration_html = bokeh_phd2(guide_logs)
        guide_logs = ','.join(iguide_logs_upload)
        print("Done.")
    elif img_id:
        guide_logs = form.get("prev_guide_logs")
        if form.get("redo_graphs") == "on":
            full_guide_logs = ','.join([os.path.join(current_app.config["UPLOAD_PATH"],i.replace("/","\\")) for i in guide_logs.split(",")])
            guiding_html,calibration_html = bokeh_phd2(full_guide_logs)
        else:
            guiding_html = tmp_img["guiding_html"]
            calibration_html = tmp_img["calibration_html"]
    else:
         guiding_html,calibration_html = "",""

    table_ids = []
    for table in [
        "camera",
        "telescope",
        "reducer",
        "mount",
        "tripod",
        "filter_wheel",
        "eaf",
        "dew_heater",
        "guide_camera",
        "oag",
    ]:
        if form.get(f"{table}_id") == "0":
            table_ids.append(None)
        else:
            table_ids.append(form.get(f"{table}_id"))

    conn = get_conn()
    cur = conn.cursor()

    if img_id:
        #editing updating
        cur.execute(
            """
            UPDATE images SET
                title=%s, description=%s, author=%s, slug=%s, image_path=%s, image_thumbnail=%s, object_type=%s,
                header_json=%s, overlays_json=%s, location=%s, location_latitude=%s,
                location_longitude=%s, location_elevation=%s, guide_log=%s, guiding_html=%s,calibration_html=%s,
                camera_id=%s, telescope_id=%s, reducer_id=%s, mount_id=%s, tripod_id=%s,
                filter_wheel_id=%s, eaf_id=%s, dew_heater_id=%s, guide_camera_id=%s, oag_id=%s
            WHERE id=%s
            """,
            (
                title, form.get("description"), user, slugify(title),img_path_upload, thumbnail_path, object_type, header_json,
                svg_image, form.get("location"), lat, lon, form.get("location_elevation"),
                guide_logs, guiding_html, calibration_html, *table_ids, img_id
            ),
        )
        # Clear and reinsert related tables
        cur.execute("DELETE FROM image_views WHERE image_id = %s", (img_id,))
        cur.execute("DELETE FROM image_likes WHERE image_id = %s", (img_id,))
        cur.execute("DELETE FROM image_comments WHERE image_id = %s", (img_id,)) 
        cur.execute("DELETE FROM capture_dates WHERE image_id = %s", (img_id,))
        cur.execute("DELETE FROM image_lights WHERE image_id = %s", (img_id,))
        cur.execute("DELETE FROM image_software WHERE image_id = %s", (img_id,)) 

    else:
        cur.execute(
            """
            INSERT INTO images (title, description, author, slug, image_path, image_thumbnail, object_type, header_json, overlays_json, location, location_latitude, location_longitude, location_elevation, guide_log,guiding_html,calibration_html,camera_id, telescope_id, reducer_id, mount_id, tripod_id, filter_wheel_id, eaf_id, dew_heater_id, guide_camera_id, oag_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, %s) RETURNING id
            """,
            (
                title,
                form.get("description"),
                user,
                slugify(title),
                img_path_upload,
                thumbnail_path,
                object_type,
                header_json,
                svg_image,
                form.get("location"),
                lat,
                lon,
                form.get("location_elevation"),
                guide_logs,
                guiding_html,
                calibration_html,
                *table_ids,
            ),
        )
        
        img_id = cur.fetchone()["id"]

    # Caputre dates
    dates = json.loads(form.get("capture_dates", "[]"))
    for d in dates:
        # print(d)
        d_obj = datetime.strptime(d, "%Y-%m-%d")
        illumination, phase_name = get_moon_illumination(d_obj)
        cur.execute(
            "INSERT INTO capture_dates (image_id, capture_date, moon_illumination, moon_phase) VALUES (%s,%s,%s,%s)",
            (img_id, d, illumination, phase_name),
        )

    # image lights
    idx = 0
    while True:
        filt = form.get(f"filter_{idx}")
        cnt = form.get(f"count_{idx}")
        exp = form.get(f"exposure_{idx}")
        gain = form.get(f"gain_{idx}")
        offset = form.get(f"offset_{idx}")
        temp = form.get(f"temperature_{idx}")
        if not filt:
            break
        cur.execute(
            "INSERT INTO image_lights (image_id, filter, light_count, exposure_time, gain, offset_cam, temperature) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (img_id, filt, cnt, exp, gain, offset, temp),
        )
        idx += 1

    # software
    for sid in form.getlist("software_ids"):
        cur.execute(
            "INSERT INTO image_software (image_id, software_id) VALUES (%s,%s)",
            (img_id, sid),
        )

    conn.commit()
    cur.close()
    flash("Post updated successfully!")
    return redirect(url_for("blog.list_images"))