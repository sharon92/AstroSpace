import os
import logging
import requests
import json
from datetime import datetime
import time
from psycopg2.extras import Json
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
    jsonify,
    make_response,
)
from collections import defaultdict

# from werkzeug.exceptions import abort
from astroquery.simbad import Simbad
from AstroSpace.auth import login_required
from AstroSpace.constants import (
    ALLOWED_RELATED_MEDIA_EXTENSIONS,
    DB_TABLES,
    IMAGE_DETAIL_TABLE_NAMES,
    IMAGE_RELATION_TABLES,
)
from AstroSpace.db import get_conn
from AstroSpace.repositories.images import (
    get_collection_filter_metadata,
    get_collection_images,
    fetch_options,
    get_all_images,
    get_image_by_id,
    get_image_tables,
)
from AstroSpace.services.authorization import require_owner
from AstroSpace.services.collection_filters import (
    PYTHON_UNIX_EPOCH_ORDINAL,
    build_active_collection_filters,
    normalize_collection_filters,
)
from AstroSpace.services.content import parse_meta_store, sanitize_rich_text
from AstroSpace.services.content import sanitize_plain_text
from AstroSpace.logging_utils import debug_log
from AstroSpace.services.cookies import COOKIE_POLICY_ROWS, consent_allows
from AstroSpace.services.engagement import (
    COMMENT_NAME_LIMIT,
    COMMENT_TEXT_LIMIT,
    CommentRateLimitError,
    apply_commenter_cookie,
    apply_visitor_cookie,
    build_visitor_identity,
    clear_commenter_cookie,
    commenter_name_from_request,
    fetch_image_engagement_state,
    like_image as register_image_like,
    record_image_view,
    submit_image_comment,
)
from AstroSpace.services.uploads import allowed_file, ensure_directory, save_user_upload
from AstroSpace.utils.moon_phase import get_moon_illumination
from AstroSpace.utils.phd2logparser import build_plotly_payloads
from AstroSpace.utils.platesolve import platesolve, get_overlays, fits_header_only
from AstroSpace.utils.utils import geocode, slugify
from AstroSpace.utils.utils import (
    ALLOWED_IMG_EXTENSIONS,
    ALLOWED_TXT_EXTENSIONS,
)

bp = Blueprint("blog", __name__)


@bp.context_processor
def inject_now():
    return {"now": datetime.now}


@bp.route("/favicon.ico")
def favicon():
    return "", 204


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
    return render_template("home.html", top_images=top_images)


@bp.route("/collection")
def collection():
    filter_metadata = get_collection_filter_metadata()
    raw_args = request.args.to_dict(flat=True)
    filter_state, query_filters = normalize_collection_filters(raw_args, filter_metadata)
    active_filters = build_active_collection_filters(
        url_for("blog.collection"),
        raw_args,
        filter_state,
    )
    debug_log("Collection filters requested: %s", {chip["label"]: chip["value"] for chip in active_filters})
    images = get_collection_images(query_filters)
    debug_log("Collection query returned %s image(s)", len(images))
    return render_template(
        "collection.html",
        images=images,
        filter_metadata=filter_metadata,
        filter_state=filter_state,
        active_filters=active_filters,
        result_count=len(images),
        unix_epoch_ordinal=PYTHON_UNIX_EPOCH_ORDINAL,
    )


@bp.route("/cookie-policy")
def cookie_policy():
    return render_template(
        "cookie_policy.html",
        cookie_policy_rows=COOKIE_POLICY_ROWS,
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
    r = requests.get(url, timeout=10)
    if r.status_code == 200:
        return str(round(r.json()["results"][0]["elevation"]))
    else:
        return "0"


@bp.route("/image/<int:image_id>/<string:image_name>")
def image_detail(image_id, image_name):
    tables = get_image_tables(image_id)
    if len(tables) == 1:
        return tables
    background_image = tables[0]["image_path"]
    images = [dict(zip(IMAGE_DETAIL_TABLE_NAMES, tables))]

    visitor_identity = build_visitor_identity()
    record_image_view(image_id, visitor_identity)
    images[0]["engagement"] = fetch_image_engagement_state(image_id, visitor_identity)

    db = get_conn()
    with db.cursor() as cur:
        cur.execute(
            "SELECT id FROM images WHERE slug = %s ORDER BY created_at DESC",
            (image_name,),
        )
        prev_images = cur.fetchall()

    for i in prev_images:
        if i["id"] != image_id:
            related_tables = get_image_tables(i["id"])
            related_image = dict(zip(IMAGE_DETAIL_TABLE_NAMES, related_tables))
            related_image["engagement"] = fetch_image_engagement_state(i["id"], visitor_identity)
            images += [related_image]

    response = make_response(
        render_template(
            "image_detail.html",
            background_image=background_image,
            images=images,
            remembered_commenter_name=commenter_name_from_request(),
            preference_cookies_enabled=consent_allows("preferences"),
        )
    )
    apply_visitor_cookie(response, visitor_identity)
    return response


@bp.route("/image/<int:image_id>/like", methods=["POST"])
def like_image_endpoint(image_id):
    image = get_image_by_id(image_id)
    if not image:
        return jsonify({"message": "Post not found."}), 404

    visitor_identity = build_visitor_identity()
    inserted = register_image_like(image_id, visitor_identity)
    engagement = fetch_image_engagement_state(image_id, visitor_identity, include_comments=False)

    response = jsonify(
        {
            "message": "Thanks for starring this post." if inserted else "You have already starred this post.",
            "liked": engagement["liked"],
            "like_count": engagement["like_count"],
        }
    )
    apply_visitor_cookie(response, visitor_identity)
    return response


@bp.route("/image/<int:image_id>/comment", methods=["POST"])
def comment_on_image(image_id):
    image = get_image_by_id(image_id)
    if not image:
        return jsonify({"message": "Post not found."}), 404

    payload = request.get_json(silent=True) or request.form
    display_name = sanitize_plain_text(payload.get("display_name"), max_length=COMMENT_NAME_LIMIT)
    comment = sanitize_plain_text(payload.get("comment"), max_length=COMMENT_TEXT_LIMIT)
    remember_name = str(payload.get("remember_name", "")).lower() in {"1", "true", "yes", "on"}

    if not display_name:
        return jsonify({"message": "Please enter a display name."}), 400
    if not comment:
        return jsonify({"message": "Please enter a comment."}), 400

    visitor_identity = build_visitor_identity()

    try:
        inserted = submit_image_comment(image_id, visitor_identity, display_name, comment)
    except CommentRateLimitError as exc:
        return jsonify({"message": str(exc)}), exc.status_code

    engagement = fetch_image_engagement_state(image_id, visitor_identity, include_comments=False)
    preferences_enabled = consent_allows("preferences")
    response = jsonify(
        {
            "message": "Comment posted.",
            "comment_count": engagement["comment_count"],
            "preferences_enabled": preferences_enabled,
            "comment": {
                "id": inserted["id"],
                "display_name": display_name,
                "comment": comment,
                "commented_at": inserted["commented_at"].isoformat(),
                "commented_at_label": inserted["commented_at"].strftime("%d %b %Y %H:%M"),
            },
        }
    )
    apply_visitor_cookie(response, visitor_identity)
    if remember_name and preferences_enabled:
        apply_commenter_cookie(response, display_name)
    else:
        clear_commenter_cookie(response)
    return response


def build_related_media_rows(form, uploaded_files, upload_root, user_id):
    raw_store = form.get("related_media_store") or "[]"
    try:
        related_media_store = json.loads(raw_store)
    except (TypeError, ValueError):
        related_media_store = []

    normalized_rows = []
    uploaded_rows = []
    for file_storage in uploaded_files:
        if file_storage and file_storage.filename:
            uploaded_rows.append(file_storage)

    upload_iter = iter(uploaded_rows)
    for row in related_media_store:
        existing_path = (row.get("existing_path") or "").strip()
        caption = (row.get("caption") or "").strip()
        if existing_path:
            normalized_rows.append({"media_path": existing_path, "caption": caption})
            continue

        upload = next(upload_iter, None)
        if not upload:
            continue

        if not allowed_file(upload.filename, ALLOWED_RELATED_MEDIA_EXTENSIONS):
            raise ValueError(
                f"Unsupported related media file: {upload.filename}. "
                "Allowed types are JPG, PNG, WEBP, GIF, MP4, WEBM, and OGG."
            )

        stored_upload = save_user_upload(upload, upload_root, user_id)
        normalized_rows.append(
            {
                "media_path": stored_upload.public_path,
                "caption": caption,
            }
        )

    for upload in upload_iter:
        if not allowed_file(upload.filename, ALLOWED_RELATED_MEDIA_EXTENSIONS):
            raise ValueError(
                f"Unsupported related media file: {upload.filename}. "
                "Allowed types are JPG, PNG, WEBP, GIF, MP4, WEBM, and OGG."
            )
        stored_upload = save_user_upload(upload, upload_root, user_id)
        normalized_rows.append({"media_path": stored_upload.public_path, "caption": ""})

    return normalized_rows

# New post form
def render_image_form(title, **kwargs):
    kwargs.update({t: fetch_options(t) for t in DB_TABLES if t not in ["guide_camera"]})
    kwargs.update({"softwares": fetch_options("software")})
    kwargs.update({"filters": fetch_options("cam_filter")})
    related_media_json = kwargs.pop("related_media_json", "[]")

    filter_options = "".join(
        [f'<option value="{f["name"]}">{f["name"]}</option>' for f in kwargs["filters"]]
    )

    option_none = '<option value="0">None</option>'

    return render_template(
        "create.html",
        title=title,
        filter_options=filter_options,
        option_none=option_none,
        related_media_json=related_media_json,
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
        related_media_json=json.dumps([]),
        is_edit=False,
    )


@bp.route("/edit/<int:image_id>")
@login_required
def edit_image(image_id):
    tables = get_image_tables(image_id, keep_original=True)
    if len(tables) == 1:
        return tables

    image, equipment_list, dates, lights, software_list, _, _, _, _, related_media = tables
    require_owner(image["author"])

    capture_dates = [d["capture_date"].strftime("%Y-%m-%d") for d in dates]

    equipment = {}
    for eq in equipment_list:
        equipment[eq["table"]] = eq["id"]

    related_media_payload = [
        {
            "existing_path": row.get("media_path") or "",
            "caption": row.get("caption") or "",
            "display_name": row.get("display_name")
            or os.path.basename((row.get("media_path") or "").replace("\\", "/")),
        }
        for row in related_media
    ]

    return render_image_form(
        "Edit Post",
        image=image,
        equipment=equipment,
        capture_dates=capture_dates,
        software_list=software_list,
        lights_json=json.dumps(lights),
        related_media_json=json.dumps(related_media_payload),
        is_edit=True,
    )


@bp.route("/delete/<int:image_id>")
@login_required
def delete_image(image_id):
    image = get_image_by_id(image_id)
    if not image:
        flash("Post not found.")
        return redirect(url_for("blog.collection"))
    require_owner(image["author"])

    conn = get_conn()
    cur = conn.cursor()
    # Clear and reinsert related tables
    for table in IMAGE_RELATION_TABLES:
        cur.execute(f"DELETE FROM {table} WHERE image_id = %s", (image_id,))
    cur.execute("DELETE FROM images WHERE id = %s", (image_id,))
    
    conn.commit()
    cur.close()
    flash("Post deleted successfully!")
    return redirect(url_for("blog.collection"))

@bp.route("/create", methods=["POST"])
@login_required
def save_image():
    user = g.user["username"]
    user_id = str(g.user["id"])
    img_id = None
    debug_log("save_image started for user=%s", user, level=logging.INFO)

    ensure_directory(os.path.join(current_app.config["UPLOAD_PATH"], user_id))

    def image_form_redirect(message):
        flash(message)
        if img_id:
            return redirect(url_for("blog.edit_image", image_id=img_id))
        return redirect(url_for("blog.new_image"))
    
    try:
        form = request.form
        img_id = form.get("image_id")
        debug_log(
            "Processing post payload (mode=%s, image_id=%s)",
            "update" if img_id else "create",
            img_id or "new",
        )
        
        if img_id:
            tmp_img = get_image_by_id(img_id)
            if tmp_img:
                require_owner(tmp_img["author"])
        
        lat = form.get("location_latitude") or None
        lon = form.get("location_longitude") or None
        if not lat or not lon:
            lat, lon = geocode(form["location"])
            debug_log(
                "Geocoded location for user=%s (location=%s, lat=%s, lon=%s)",
                user,
                form.get("location"),
                lat,
                lon,
            )
        else:
            debug_log("Using submitted coordinates for user=%s", user)
        if lat is None or lon is None:
            debug_log(
                "Location coordinates could not be resolved for location=%s",
                form.get("location"),
                level=logging.WARNING,
            )
        
        title = form.get("title")
        
        Simbad.reset_votable_fields()
        Simbad.add_votable_fields("otype_txt")
            
        debug_log("Querying SIMBAD for title=%s", title)
        query = Simbad.query_object(title)
        object_type = "Unknown"
        if query and len(query) > 0:
            title = query[0]["main_id"].replace("NAME", "").strip()
            object_type = query[0]["otype_txt"]
            debug_log("SIMBAD resolved title=%s object_type=%s", title, object_type)
        else:
            debug_log("SIMBAD returned no result for title=%s", title)

        file = request.files.get("image_path")
        fits_path = request.files.get("fits_file")
        starless_file = request.files.get("starless_image_path")
        svg_image = None
        if file and file.filename:
            debug_log("Received preview image upload filename=%s", file.filename)
            if not allowed_file(file.filename, ALLOWED_IMG_EXTENSIONS):
                debug_log(
                    "Rejected preview image with unsupported extension: %s",
                    file.filename,
                    level=logging.WARNING,
                )
                return image_form_redirect("Preview image must be a JPG or PNG file.")

            stored_image = save_user_upload(file, current_app.config["UPLOAD_PATH"], user_id)
            image_path = stored_image.absolute_path
            img_path_upload = stored_image.public_path
            header_json, thumbnail_path, pixel_scale = platesolve(
                image_path, user_id, fits_path
            )
            debug_log(
                "Preview image persisted (public_path=%s, thumbnail=%s, pixel_scale=%s)",
                img_path_upload,
                thumbnail_path,
                pixel_scale,
            )
            
        elif img_id:
            img_path_upload = form.get("prev_img")
            if form.get("redo_plate_solve") == "on":
                debug_log("Redoing plate solve for image_id=%s", img_id)
                full_img_path = os.path.join(
                    current_app.config["UPLOAD_PATH"], img_path_upload.replace("/", "\\")
                )
                header_json, thumbnail_path, pixel_scale = platesolve(
                    full_img_path, user_id, fits_path
                )
                
            elif form.get("regenerate_overlays") == "on":
                debug_log("Regenerating overlays for image_id=%s without re-plate-solving", img_id)
                header_json = tmp_img["header_json"]
                thumbnail_path = tmp_img["image_thumbnail"]
                pixel_scale = tmp_img["pixel_scale"]
            else:
                debug_log("Reusing existing plate solve artifacts for image_id=%s", img_id)
                header_json = tmp_img["header_json"]
                svg_image = tmp_img["overlays_json"]
                thumbnail_path = tmp_img["image_thumbnail"]
                pixel_scale = tmp_img["pixel_scale"]
        else:
            debug_log("Rejecting new post because preview image is missing.", level=logging.WARNING)
            return image_form_redirect("A preview image is required when creating a post.")

        starless_path_upload = form.get("prev_starless_img") or ""
        if starless_file and starless_file.filename:
            debug_log("Received starless image upload filename=%s", starless_file.filename)
            if not allowed_file(starless_file.filename, ALLOWED_IMG_EXTENSIONS):
                debug_log(
                    "Rejected starless image with unsupported extension: %s",
                    starless_file.filename,
                    level=logging.WARNING,
                )
                return image_form_redirect("Starless image must be a JPG or PNG file.")

            stored_starless = save_user_upload(starless_file, current_app.config["UPLOAD_PATH"], user_id)
            starless_path_upload = stored_starless.public_path
            debug_log("Starless image persisted (public_path=%s)", starless_path_upload)

        try:
            related_media_rows = build_related_media_rows(
                form,
                request.files.getlist("related_media_files"),
                current_app.config["UPLOAD_PATH"],
                user_id,
            )
        except ValueError as exc:
            debug_log(
                "Rejected related media submission for user=%s: %s",
                user,
                exc,
                level=logging.WARNING,
            )
            return image_form_redirect(str(exc))
        debug_log("Prepared %s related media row(s) for image submission.", len(related_media_rows))

        if svg_image is None:
            svg_image = json.dumps(get_overlays(header_json))
        guide_logs = request.files.getlist("guide_logs")
        new_guide_logs = any(i.filename for i in guide_logs)

        if new_guide_logs:
            debug_log(
                "Generating guiding plots from %s uploaded guide log(s).",
                sum(1 for guide_log in guide_logs if guide_log.filename),
            )
            iguide_logs = []
            iguide_logs_upload = []
            for guide_log in guide_logs:
                if guide_log and allowed_file(guide_log.filename, ALLOWED_TXT_EXTENSIONS):
                    stored_log = save_user_upload(guide_log, current_app.config["UPLOAD_PATH"], user_id)
                    iguide_logs.append(stored_log.absolute_path)
                    iguide_logs_upload.append(stored_log.public_path)
            guide_logs = ",".join(iguide_logs)
            guiding_plot, calibration_plot = build_plotly_payloads(guide_logs)
            guiding_plot_json = Json(guiding_plot)
            calibration_plot_json = Json(calibration_plot)
            guide_logs = ",".join(iguide_logs_upload)
        elif img_id:
            guide_logs = form.get("prev_guide_logs") or ""
            if form.get("redo_graphs") == "on":
                debug_log("Regenerating guiding plots for image_id=%s", img_id)
                full_guide_logs = ",".join(
                    [
                        os.path.join(
                            current_app.config["UPLOAD_PATH"], i.replace("/", "\\")
                        )
                        for i in guide_logs.split(",")
                    ]
                )
                guiding_plot, calibration_plot = build_plotly_payloads(full_guide_logs)
                guiding_plot_json = Json(guiding_plot)
                calibration_plot_json = Json(calibration_plot)
            else:
                debug_log("Reusing existing guiding plots for image_id=%s", img_id)
                guiding_plot_json = Json(tmp_img["guiding_plot_json"]) if tmp_img.get("guiding_plot_json") else None
                calibration_plot_json = Json(tmp_img["calibration_plot_json"]) if tmp_img.get("calibration_plot_json") else None
        else:
            guide_logs = ""
            guiding_plot_json, calibration_plot_json = None, None
        
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
        debug_log("Sanitizing rich text content for image submission.")
        clean_desc = sanitize_rich_text(desc)

        conn = get_conn()
        cur = conn.cursor()

        column_list = [
            "title",
            "short_description",
            "description",
            "author",
            "slug",
            "created_at",
            "edited_at",
            "image_path",
            "starless_image_path",
            "image_thumbnail",
            "pixel_scale",
            "object_type",
            "header_json",
            "overlays_json",
            "meta_json",
            "location",
            "location_latitude",
            "location_longitude",
            "location_elevation",
            "guide_log",
            "guiding_plot_json",
            "calibration_plot_json",
            *[f"{i}_id" for i in DB_TABLES],
        ]

        placeholders = ", ".join(["%s"] * len(column_list))

        values = [
            title,
            form.get("short_description"),
            clean_desc,
            user,
            slugify(title),
            created_at,
            edited_at,
            img_path_upload,
            starless_path_upload,
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
            guiding_plot_json,
            calibration_plot_json,
            *table_ids,
        ]

        if img_id:
            # editing updating
            debug_log("Updating existing image row image_id=%s", img_id)
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
            for table in IMAGE_RELATION_TABLES:
                cur.execute(f"DELETE FROM {table} WHERE image_id = %s", (img_id,))

        else:
            debug_log("Inserting new image row for title=%s", title)
            query = f"INSERT INTO images ({', '.join(column_list)}) VALUES ({placeholders}) RETURNING id"
            cur.execute(
                query,
                (*values,),
            )

            img_id = cur.fetchone()["id"]
            debug_log("Inserted new image row image_id=%s", img_id)

        # Caputre dates
        dates = json.loads(form.get("capture_dates", "[]"))
        software_ids = form.getlist("software_ids")
        debug_log(
            "Persisting related rows for image_id=%s (capture_dates=%s, software_ids=%s)",
            img_id,
            len(dates),
            len(software_ids),
        )
        for d in dates:
            d_obj = datetime.strptime(d, "%Y-%m-%d")
            illumination, phase_name = get_moon_illumination(d_obj)
            cur.execute(
                "INSERT INTO capture_dates (image_id, capture_date, moon_illumination, moon_phase) VALUES (%s,%s,%s,%s)",
                (img_id, d, illumination, phase_name),
            )

        # image lights
        idx = 0
        light_rows = 0
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
            light_rows += 1

        # software
        for sid in software_ids:
            cur.execute(
                "INSERT INTO image_software (image_id, software_id) VALUES (%s,%s)",
                (img_id, sid),
            )

        for order, media in enumerate(related_media_rows):
            cur.execute(
                """
                INSERT INTO related_image_media (image_id, media_path, caption, sort_order)
                VALUES (%s, %s, %s, %s)
                """,
                (img_id, media["media_path"], media["caption"], order),
            )

        conn.commit()
        cur.close()
        debug_log(
            "save_image committed successfully (image_id=%s, light_rows=%s, related_media=%s)",
            img_id,
            light_rows,
            len(related_media_rows),
            level=logging.INFO,
        )
        flash("Post updated successfully!")
        return redirect(url_for("private.profile", tab="Posts"))
    except Exception as e:
        current_app.logger.exception("Failed to save image for user=%s image_id=%s", user, img_id or "new")
        return image_form_redirect(f"An error occurred while saving the post: {e}")
