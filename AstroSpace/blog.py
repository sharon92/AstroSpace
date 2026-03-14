import os
from numpy import log
import requests
import json
from datetime import datetime
import time
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
    jsonify
)
from collections import defaultdict

# from werkzeug.exceptions import abort
from astroquery.simbad import Simbad
from AstroSpace.auth import login_required
from AstroSpace.constants import DB_TABLES
from AstroSpace.db import get_conn
from AstroSpace.repositories.images import (
    fetch_options,
    get_all_images,
    get_image_by_id,
    get_image_tables,
)
from AstroSpace.services.content import parse_meta_store, sanitize_rich_text
from AstroSpace.services.uploads import allowed_file, ensure_directory, save_user_upload
from AstroSpace.utils.moon_phase import get_moon_illumination
from AstroSpace.utils.phd2logparser import build_plotly_payloads
from AstroSpace.utils.platesolve import platesolve, get_overlays, fits_header_only
from AstroSpace.utils.utils import geocode, slugify
from AstroSpace.utils.blog_form import BlogForm
from AstroSpace.utils.utils import (
    ALLOWED_IMG_EXTENSIONS,
    ALLOWED_TXT_EXTENSIONS,
)

from werkzeug.utils import secure_filename

bp = Blueprint("blog", __name__)


@bp.context_processor
def inject_now():
    return {"now": datetime.now}


@bp.route("/uploads/<path:filename>")
def upload(filename):
    path = os.path.join(current_app.config["UPLOAD_PATH"], filename)
    last_modified = time.gmtime(os.path.getmtime(path))
    return send_from_directory(current_app.config["UPLOAD_PATH"], filename, last_modified = last_modified)


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
        "home.html",top_images=top_images
    )


@bp.route("/collection")
def collection():
    images = get_all_images(unique=True)
    return render_template(
        "collection.html", images=images
        )

@bp.route("/extract_stats", methods=["POST"])
def extract_stats():
    file = request.files.get("wbpp_log_file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400
    
    # with open(log) as f:
    #     content = f.readlines()
    content = file.read().decode("utf-8").splitlines()

    stats = {}
    wts = []
    for n,line in enumerate(content):
        if " FWHM              :" in line:
            Name = os.path.basename(content[n-2].split(" ")[-1].strip()).replace("_c","").replace("_d","").replace(".xisf","")
            FWHM = float(line.split(" ")[-2].strip())
            stats[Name] = {"FWHM": FWHM}
        elif " Eccentricity      :" in line:
            stats[Name]["Eccentricity"] = float(line.split(" ")[-1].strip())
        elif " Number of stars   :" in line:
            stats[Name]["Number of stars"] = int(line.split(" ")[-1].strip())
        elif " PSF Signal Weight :" in line:
            stats[Name]["PSF Signal Weight"] = float(line.split(" ")[-1].strip())   
        elif " PSF SNR           :" in line:
            stats[Name]["PSF SNR"] = float(line.split(" ")[-1].strip())
        elif " SNR               :" in line:
            stats[Name]["SNR"] = float(line.split(" ")[-1].strip())
        elif " Median (ADU)      :" in line:
            stats[Name]["Median (ADU)"] = float(line.split(" ")[-1].strip())
        elif " MAD (ADU)         : " in line:
            stats[Name]["MAD (ADU)"] = float(line.split(" ")[-1].strip())
        elif " Mstar (ADU)       : " in line:
            stats[Name]["Mstar (ADU)"] = float(line.split(" ")[-1].strip())
        elif " Normalized image weights:" in line: 
            wts += [n]

    for line in content[wts[-1]+1:]:
        if " Integration of " in line:
            break
        ls = line.split(" ")
        if '.xisf' in line:
            Name = os.path.basename(ls[-1].strip()).replace("_c","").replace("_d","").replace("_r","").replace(".xisf","")
        elif len(ls) > 3: 
            weights  = list(map(float, ls[-3:]))
            stats[Name]["WBPP weight 1"] = weights[0]
            stats[Name]["WBPP weight 2"] = weights[1]
            stats[Name]["WBPP weight 3"] = weights[2]

    return jsonify(stats)


@bp.route("/extract_meta", methods=["POST"])
def extract_keywords():
    files = request.files.getlist("header_files")
    if not files:
        return jsonify({"error": "No file uploaded"}), 400

    try:
        
        if 'meta_store' in request.files:
            meta_store = json.load(request.files['meta_store'])
            all_meta = meta_store.get("meta", [])
            filenames = meta_store.get("filenames", [])
            wbpp_stats = meta_store.get("wbpp_stats", {})
        else:
            all_meta = []
            filenames = []
            wbpp_stats = {}

        for f in files:
            meta = fits_header_only(f, return_dict=True)
            name = os.path.splitext(f.filename.replace(".header", ""))[0]
            filenames.append(name)
            for key in wbpp_stats.keys():
                if key.startswith(name):
                    for k,v in wbpp_stats[key].items():
                        if k not in meta:
                            meta[k] = {"v": v, "c": ""}
            all_meta.append(meta)

        if not all_meta:
            return jsonify({"error": "No valid headers received"}), 400

        constant = {}
        variable = defaultdict(list)
        comments = {k: v["c"] for k, v in all_meta[0].items()}
        keys = all_meta[0].keys()

        for key in keys:
            values = [m[key]["v"] for m in all_meta if key in m]

            # all values identical → constant
            if all(v == values[0] for v in values):
                constant[key] = values[0]
            else:
                variable[key] = values

        variable["_files"] = filenames

        return jsonify({
            "meta": all_meta,
            "filenames": filenames,
            "constant": constant,
            "variable": variable,
            "comments": comments
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        "meta_json",
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
    )

# New post form
def render_image_form(title, **kwargs):
    kwargs.update({t: fetch_options(t) for t in DB_TABLES if t not in ["guide_camera"]})
    kwargs.update({"softwares": fetch_options("software")})
    kwargs.update({"filters": fetch_options("cam_filter")})

    filter_options = "".join(
        [f'<option value="{f["name"]}">{f["name"]}</option>' for f in kwargs["filters"]]
    )

    option_none = '<option value="0">None</option>'

    return render_template(
        "create.html",
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

    image, equipment_list, dates, lights, software_list, _, _, _, _ = tables

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


@bp.route("/delete/<int:image_id>")
@login_required
def delete_image(image_id):
    conn = get_conn()
    cur = conn.cursor()
    # Clear and reinsert related tables
    for table in [
        "image_views",
        "image_likes",
        "image_comments",
        "capture_dates",
        "image_lights",
        "image_software",
    ]:
        cur.execute(f"DELETE FROM {table} WHERE image_id = %s", (image_id,))
    cur.execute("DELETE FROM images WHERE id = %s", (image_id,))
    
    conn.commit()
    cur.close()
    flash("Post deleted successfully!")
    return redirect(url_for("blog.collection"))

@bp.route("/create", methods=["POST"])
@login_required
def save_image():
    print("Saving/Updating image...")
    user = g.user["username"]
    user_id = str(g.user["id"])

    ensure_directory(os.path.join(current_app.config["UPLOAD_PATH"], user_id))
    
    try:
        print("Processing form data...")
        form = request.form
        img_id = form.get("image_id")
        
        if img_id:
            tmp_img = get_image_by_id(img_id)
        
        lat = form.get("location_latitude") or None
        lon = form.get("location_longitude") or None
        if not lat or not lon:
            lat, lon = geocode(form["location"])
        
        title = form.get("title")
        
        Simbad.reset_votable_fields()
        Simbad.add_votable_fields("otype_txt")
            
        print("Performing object lookup...")
        query = Simbad.query_object(title)
        object_type = "Unknown"
        if query and len(query) > 0:
            title = query[0]["main_id"].replace("NAME", "").strip()
            object_type = query[0]["otype_txt"]

        file = request.files.get("image_path")
        fits_path = request.files.get("fits_file")
        #print("Performing plate solving...")
        svg_image = None
        if file.filename and allowed_file(file.filename, ALLOWED_IMG_EXTENSIONS):
            stored_image = save_user_upload(file, current_app.config["UPLOAD_PATH"], user_id)
            image_path = stored_image.absolute_path
            img_path_upload = stored_image.public_path
            header_json, thumbnail_path, pixel_scale = platesolve(
                image_path, user_id, fits_path
            )
            
        elif img_id:
            img_path_upload = form.get("prev_img")
            if form.get("redo_plate_solve") == "on":
                full_img_path = os.path.join(
                    current_app.config["UPLOAD_PATH"], img_path_upload.replace("/", "\\")
                )
                header_json, thumbnail_path, pixel_scale = platesolve(
                    full_img_path, user_id, fits_path
                )
                
            elif form.get("regenerate_overlays") == "on":
                header_json = tmp_img["header_json"]
                thumbnail_path = tmp_img["image_thumbnail"]
                pixel_scale = tmp_img["pixel_scale"]
            else:
                header_json = tmp_img["header_json"]
                svg_image = tmp_img["overlays_json"]
                thumbnail_path = tmp_img["image_thumbnail"]
                pixel_scale = tmp_img["pixel_scale"]

        if svg_image is None:
            svg_image = json.dumps(get_overlays(header_json))
        guide_logs = request.files.getlist("guide_logs")
        new_guide_logs = any(i.filename for i in guide_logs)

        if new_guide_logs:
            print("Generating guide log plot...")
            iguide_logs = []
            iguide_logs_upload = []
            for file in guide_logs:
                if file and allowed_file(file.filename, ALLOWED_TXT_EXTENSIONS):
                    stored_log = save_user_upload(file, current_app.config["UPLOAD_PATH"], user_id)
                    iguide_logs.append(stored_log.absolute_path)
                    iguide_logs_upload.append(stored_log.public_path)
            guide_logs = ",".join(iguide_logs)
            guiding_plot, calibration_plot = build_plotly_payloads(guide_logs)
            guiding_html = json.dumps(guiding_plot)
            calibration_html = json.dumps(calibration_plot)
            guide_logs = ",".join(iguide_logs_upload)
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
                guiding_plot, calibration_plot = build_plotly_payloads(full_guide_logs)
                guiding_html = json.dumps(guiding_plot)
                calibration_html = json.dumps(calibration_plot)
            else:
                guiding_html = tmp_img["guiding_html"]
                calibration_html = tmp_img["calibration_html"]
        else:
            guide_logs = ""
            guiding_html, calibration_html = "", ""
        
        meta_json = parse_meta_store(request.form.get("meta_store"))
        if meta_json == "{}" and img_id:
            meta_json = tmp_img["meta_json"]

        table_ids = []
        for table in DB_TABLES:
            if form.get(f"{table}_id") == "0":
                table_ids.append(None)
            else:
                table_ids.append(form.get(f"{table}_id"))

        created_at = form.get("created_at")
        edited_at = datetime.now().strftime("%Y-%m-%d")

        # Get raw description from form
        desc = form.get("description")

        # Sanitize it
        print("Sanitizing description...")
        clean_desc = sanitize_rich_text(desc)

        conn = get_conn()
        cur = conn.cursor()

        columns = """
            title, short_description, description, author, slug,
            created_at, edited_at,
            image_path, image_thumbnail, pixel_scale, object_type,
            header_json, overlays_json, meta_json, location,
            location_latitude, location_longitude, location_elevation,
            guide_log, guiding_html, calibration_html,
        """.strip()
        columns += ",".join([f"{i}_id" for i in DB_TABLES])

        placeholders = ", ".join(["%s"] * len(columns.split(",")))

        values = [
            title,
            form.get("short_description"),
            clean_desc,
            user,
            slugify(title),
            created_at,
            edited_at,
            img_path_upload,
            thumbnail_path,
            pixel_scale,
            object_type,
            header_json,
            svg_image,
            meta_json,
            form.get("location"),
            lat,
            lon,
            form.get("location_elevation"),
            guide_logs,
            guiding_html,
            calibration_html,
            *table_ids,
        ]

        if img_id:
            # editing updating
            print("Updating existing image...")
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
                    *values,
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
            print("Inserting new image...")
            query = f"INSERT INTO images ({columns}) VALUES ({placeholders}) RETURNING id"
            cur.execute(
                query,
                (*values,),
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
        print("Done.")
        flash("Post updated successfully!")
        return redirect(url_for("private.profile"))
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("Error:", str(e))
        #flash(f"An error occurred: {str(e)}", "error")
        return '', 204
