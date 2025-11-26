# private profile - what the user can see and edit
import os
import bleach
from flask import Blueprint, render_template, current_app, g, request, jsonify
from AstroSpace.db import get_conn
from AstroSpace.auth import login_required
from AstroSpace.utils.utils import (
    ALLOWED_IMG_EXTENSIONS,
    resize_image,
    ALLOWED_TAGS,
    ALLOWED_ATTRIBUTES,
)
from werkzeug.utils import secure_filename

bp = Blueprint("private", __name__, url_prefix="/private")

ALLOWED_IMG_EXTENSIONS = {"jpg", "jpeg"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMG_EXTENSIONS

@bp.route("/profile")
@login_required
def profile():

    tabs = ["Posts", "Inventory", "Settings"]

    db = get_conn()
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, title, short_description, image_thumbnail, slug, created_at FROM images WHERE author = %s ORDER BY created_at DESC",
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
        web_info = {}

    inventory = [   
        "telescope",
        "reducer",
        "camera",
        "mount",
        "tripod",
        "guider",
        "cam_filter",
        "filter_wheel",
        "rotator",
        "dew_heater",
        "flat_panel",
        "eaf",
        "software"
    ]

    inventory_dict = {}
    with db.cursor() as cur:
        for item in inventory:
            inventory_dict[item] = {}
            
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

            cur.execute(
                f"SELECT * FROM {item}",
            )
            values = cur.fetchall()

            for obj in values:
                inventory_dict[item][obj["name"]] = obj

    return render_template(
        "profile.html",
        posts=posts,
        inventory=inventory_dict,
        user_settings=settings,
        tabs=tabs,
        data_type=data_type,
        WebName=current_app.config["TITLE"],
        web_info = web_info
    )

@bp.route("/update_inventory", methods=["POST"])
def update_inventory():
    data = request.get_json()
    table = data.get("type")
    values = data.get("values")
    tid = values.pop("id")
    name = values["name"]
    columns = ", ".join(values.keys())             
    placeholders = ", ".join(["%s"] * len(values)) 
    
    db = get_conn()
    
    if tid == -1:
        print(f"Inserting {table} -> {name} with {values}")
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING id"
       
        with db.cursor() as cur:
            cur.execute(
                query,
                tuple(values.values()),
            )
            new_id = cur.fetchone()["id"]
            print(f"Inserted with new id: {new_id}")

    else:
        print(f"Updating {table} -> {name} with {values}")
        column_list = [col.strip() for col in columns.split(",") if col.strip()]
        set_clause = ", ".join([f"{col} = %s" for col in column_list])

        query = f"""
            UPDATE {table}
            SET {set_clause}
            WHERE id = %s
        """

        with db.cursor() as cur:
            cur.execute(
                query,
                (
                    *tuple(values.values()),
                    tid
                ),
            )
    
    db.commit()
    cur.close()

    return jsonify({"message": "Inventory updated successfully"}), 200

@bp.route("/update_settings", methods=["POST"])
def update_settings():
    db = get_conn()

    user = g.user["username"]
    user_id = str(g.user["id"])
    print(f"User: {user}  ID: {user_id}")

    # Required columns
    required_columns = {
        "display_name": "TEXT",
        "display_image": "TEXT",
        "bio": "TEXT",
        "astrometry_api_key": "TEXT",
        "open_weather_api_key": "TEXT",
        "telescopius_api_key": "TEXT",
    }

    with db.cursor() as cur:
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='users'")
        existing_cols = {row["column_name"] for row in cur.fetchall()}

        for col, col_type in required_columns.items():
            if col not in existing_cols:
                print(f"Column missing → adding: {col}")
                cur.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")

    db.commit()

    # Get form values
    display_name = request.form.get("display_name")
    bio = request.form.get("bio")
    astrometry_api_key = request.form.get("astrometry_api")
    open_weather_api_key = request.form.get("owm_api")
    telescopius_api_key = request.form.get("telescopius_api")

    bio = bleach.clean(
        bio,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True   # strips disallowed tags completely (instead of escaping)
    )

    display_image = request.files.get("display_image")
    filename_to_store = ""

    # ---- Image Upload ----
    if display_image and display_image.filename and allowed_file(display_image.filename):

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
            print("ERROR saving image:", e)

    # ---- Update user row ----
    print("Updating users table...")
    print(display_name, bio, astrometry_api_key, open_weather_api_key, telescopius_api_key, user_id)
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
        print("User settings updated.")
    except Exception as e:
        print("ERROR updating users table:", e)

    # ---- WEB INFO ----
    welcome_note = request.form.get("welcome_note")
    welcome_note = bleach.clean(
        welcome_note,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True   # strips disallowed tags completely (instead of escaping)
    )


    site_name = request.form.get("site_name")

    try:
        with db.cursor() as cur:
            # Check if table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    AND table_name = 'web_info'
                )
            """)
            exists = cur.fetchone()["exists"]
            print("web_info exists:", exists)

            if not exists:
                print("Creating web_info table...")
                cur.execute("""
                    CREATE TABLE web_info (
                        id SERIAL PRIMARY KEY,
                        site_name TEXT,
                        site_description TEXT,
                        welcome_message TEXT,
                        contact_email TEXT,
                        social_links JSONB
                    );
                """)
                db.commit()

            else:
                print("Checking web_info columns...")
                cur.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'web_info'
                """)
                existing_web_cols = {row["column_name"] for row in cur.fetchall()}

                for col in ["site_name", "welcome_message"]:
                    if col not in existing_web_cols:
                        cur.execute(f"ALTER TABLE web_info ADD COLUMN {col} TEXT;")
                        db.commit()

    except Exception as e:
        print("ERROR checking/creating web_info:", e)

    db.commit()

    print("Updating web_info content...")

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
        print("web_info updated.")

    except Exception as e:
        print("ERROR updating web_info:", e)

    print("=== DONE ===")
    return jsonify({"status": "ok"})
