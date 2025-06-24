import os
import requests
import json
from datetime import datetime
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
    current_app,
    g,
    send_from_directory,
)

# from werkzeug.exceptions import abort
from astroquery.simbad import Simbad
from AstroSpace.auth import login_required
from AstroSpace.db import get_conn
from AstroSpace.utils.moon_phase import get_moon_illumination
from AstroSpace.utils.phd2logparser import bokeh_phd2
from AstroSpace.utils.platesolve import platesolve
from AstroSpace.utils.queries import (
    DB_TABLES,
    get_image_tables,
    get_all_images,
    get_image_by_id,
    fetch_options,
)
from AstroSpace.utils.utils import geocode, slugify
from AstroSpace.utils.blog_form import BlogForm

from werkzeug.utils import secure_filename

bp = Blueprint("blog", __name__)

ALLOWED_IMG_EXTENSIONS = {"jpg", "jpeg"}
ALLOWED_TXT_EXTENSIONS = {"txt"}


@bp.context_processor
def inject_now():
    return {"now": datetime.now}


@bp.route("/uploads/<path:filename>")
def upload(filename):
    return send_from_directory(current_app.config["UPLOAD_PATH"], filename)


# List view
@bp.route("/")
@bp.route("/home")
def home():
    top_images = get_all_images(unique=True, limit=10)
    for img in top_images:
        # If you want thumbnails, use `image_thumbnail` instead
        img["blog_url"] = url_for(
            "blog.image_detail", image_id=img["id"], image_name=img["slug"]
        )
        img["url"] = url_for("blog.upload", filename=img["image_path"])
    # print("Top images:", top_images)
    return render_template(
        "home.html", WebName=current_app.config["TITLE"], top_images=top_images
    )

@bp.route("/collection")
def collection():
    images = get_all_images(unique=True)
    return render_template(
        "collection.html", images=images, WebName=current_app.config["TITLE"]
    )

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


@bp.route("/blog", methods=["GET", "POST"])
@login_required
def new_blog():
    form = BlogForm()
    if form.validate_on_submit():
        title = form.title.data
        content = request.form.get("content")  # This is from Quill's hidden input
        image = form.image.data

        image_path = None
        if image:
            filename = secure_filename(image.filename)
            image_path = os.path.join(current_app.config["UPLOAD_PATH"], filename)
            image.save(image_path)

        # Save blog post (in database, for example)
        # Blog(title=title, content=content, image_path=image_path).save()

        flash("Blog post created successfully!")
        return redirect(url_for("your_blog_listing_view"))

    return render_template(
        "create_blog.html", form=form, WebName=current_app.config["TITLE"]
    )


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
    table_names = [
        "image",
        "equipment_list",
        "dates",
        "lights",
        "software_list",
        "guiding_html",
        "calibration_html",
        "svg_image",
    ]
    # image, equipment_list, dates, lights, software_list, guiding_html, calibration_html,svg_image = tables
    images = [dict(zip(table_names, tables))]

    db = get_conn()
    with db.cursor() as cur:
        cur.execute(
            "SELECT id FROM images WHERE slug = %s ORDER BY created_at DESC",
            (image_name,),
        )
        prev_images = cur.fetchall()

    for i in prev_images:
        if i["id"] != image_id:
            images += [dict(zip(table_names, get_image_tables(i["id"])))]

    return render_template(
        "image_detail.html",
        background_image=background_image,
        images=images,
        WebName=current_app.config["TITLE"],
    )


# List view
@bp.route("/posts")
@login_required
def list_images():
    db = get_conn()
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, title, created_at FROM images WHERE author = %s ORDER BY created_at DESC",
            (g.user["username"],),
        )
        posts = cur.fetchall()

    return render_template(
        "user_posts.html", posts=posts, WebName=current_app.config["TITLE"]
    )


# New post form
def render_image_form(title, **kwargs):
    kwargs.update({t:fetch_options(t) for t in DB_TABLES if t not in ["guide_camera"]})
    kwargs.update({"softwares":fetch_options("software")})
    kwargs.update({"filters":fetch_options("cam_filter")})

    filter_options = "".join(
        [f'<option value="{f["name"]}">{f["name"]}</option>' for f in kwargs["filters"]]
    )

    option_none = '<option value="0">None</option>'

    return render_template(
        "create.html",
        WebName=current_app.config["TITLE"],
        title=title,
        filter_options=filter_options,
        option_none=option_none,
        **kwargs,
    )


@bp.route("/new")
@login_required
def new_image():
    return render_image_form(
        "New Post",
        equipment={},
        capture_dates=[],
        software_list=[],
        lights_json=json.dumps([]),
        is_edit=False,
    )


@bp.route("/edit/<int:image_id>")
@login_required
def edit_image(image_id):
    tables = get_image_tables(image_id, keep_original=True)
    if len(tables) == 1:
        return tables

    image, equipment_list, dates, lights, software_list, _, _, _ = tables

    capture_dates = [d["capture_date"].strftime("%Y-%m-%d") for d in dates]

    equipment = {}
    for eq in equipment_list:
        equipment[eq["table"]] = eq["id"]

    return render_image_form(
        "Edit Post",
        image=image,
        equipment=equipment,
        capture_dates=capture_dates,
        software_list=software_list,
        lights_json=json.dumps(lights),
        is_edit=True,
    )


@bp.route("/delete")
@login_required
def delete_image(img_id):
    conn = get_conn()
    cur = conn.cursor()
            # Clear and reinsert related tables
    for table in [
        "images",
        "image_views",
        "image_likes",
        "image_comments",
        "capture_dates",
        "image_lights",
        "image_software",
    ]:
        cur.execute(f"DELETE FROM {table} WHERE image_id = %s", (img_id,))

    conn.commit()
    cur.close()
    flash("Post deleted successfully!")
    return redirect(url_for("blog.list_images"))


def allowed_file(filename, allowed_extensions=ALLOWED_IMG_EXTENSIONS):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


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
        header_json, svg_image, thumbnail_path = platesolve(image_path, user_id)
    elif img_id:
        img_path_upload = form.get("prev_img")
        if form.get("redo_plate_solve") == "on":
            full_img_path = os.path.join(
                current_app.config["UPLOAD_PATH"], img_path_upload.replace("/", "\\")
            )
            header_json, svg_image, thumbnail_path = platesolve(full_img_path, user_id)
        else:
            header_json = tmp_img["header_json"]
            svg_image = tmp_img["overlays_json"]
            thumbnail_path = tmp_img["image_thumbnail"]

    guide_logs = request.files.getlist("guide_logs")
    new_guide_logs = any(i.filename for i in guide_logs)
    
    if new_guide_logs:
        print("Generating guide log plot...")
        iguide_logs = []
        iguide_logs_upload = []
        for file in guide_logs:
            if file and allowed_file(file.filename, ALLOWED_TXT_EXTENSIONS):
                filename = secure_filename(file.filename)
                guide_log_path = os.path.join(
                    current_app.config["UPLOAD_PATH"], user_id, filename
                )
                file.save(guide_log_path)
                iguide_logs.append(guide_log_path)
                iguide_logs_upload.append(f"{user_id}/{filename}")
        guide_logs = ",".join(iguide_logs)
        guiding_html, calibration_html = bokeh_phd2(guide_logs)
        guide_logs = ",".join(iguide_logs_upload)
        print("Done.")
    elif img_id:
        guide_logs = form.get("prev_guide_logs")
        if form.get("redo_graphs") == "on":
            full_guide_logs = ",".join(
                [
                    os.path.join(
                        current_app.config["UPLOAD_PATH"], i.replace("/", "\\")
                    )
                    for i in guide_logs.split(",")
                ]
            )
            guiding_html, calibration_html = bokeh_phd2(full_guide_logs)
        else:
            guiding_html = tmp_img["guiding_html"]
            calibration_html = tmp_img["calibration_html"]
    else:
        guide_logs = ""
        guiding_html, calibration_html = "", ""

    table_ids = []
    for table in DB_TABLES:
        if form.get(f"{table}_id") == "0":
            table_ids.append(None)
        else:
            table_ids.append(form.get(f"{table}_id"))

    created_at = form.get("created_at")
    edited_at = datetime.now().strftime("%Y-%m-%d")

    conn = get_conn()
    cur = conn.cursor()

    columns = """
        title, short_description, description, author, slug,
        created_at, edited_at,
        image_path, image_thumbnail, object_type,
        header_json, overlays_json, location,
        location_latitude, location_longitude, location_elevation,
        guide_log, guiding_html, calibration_html,
    """.strip()
    columns += ",".join([f"{i}_id" for i in DB_TABLES])

    placeholders = ", ".join(["%s"] * len(columns.split(",")))

    if img_id:
        # editing updating
        column_list = [col.strip() for col in columns.split(",") if col.strip()]
        set_clause = ", ".join([f"{col} = %s" for col in column_list])

        query = f"""
            UPDATE images
            SET {set_clause}
            WHERE id = %s
        """
        cur.execute(
            query,
            (
                title,
                form.get("short_description"),
                form.get("description"),
                user,
                slugify(title),
                created_at,
                edited_at,
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
                img_id,
            ),
        )
        # Clear and reinsert related tables
        for table in [
            "image_views",
            "image_likes",
            "image_comments",
            "capture_dates",
            "image_lights",
            "image_software",
        ]:
            cur.execute(f"DELETE FROM {table} WHERE image_id = %s", (img_id,))

    else:
        query = f"INSERT INTO images ({columns}) VALUES ({placeholders}) RETURNING id"
        cur.execute(
            query,
            (
                title,
                form.get("short_description"),
                form.get("description"),
                user,
                slugify(title),
                created_at,
                edited_at,
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
            "INSERT INTO image_lights (image_id, cam_filter, light_count, exposure_time, gain, offset_cam, temperature) VALUES (%s,%s,%s,%s,%s,%s,%s)",
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
