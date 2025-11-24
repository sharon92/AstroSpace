# private profile - what the user can see and edit
from flask import Blueprint, render_template, current_app, g, request, jsonify
from AstroSpace.db import get_conn
from AstroSpace.auth import login_required

bp = Blueprint("private", __name__, url_prefix="/private")

@bp.route("/profile")
@login_required
def profile():

    db = get_conn()
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, title, slug, created_at FROM images WHERE author = %s ORDER BY created_at DESC",
            (g.user["username"],),
        )
        posts = cur.fetchall()

    # Define tabs
    tabs = ["Posts", "Inventory", "Settings"]

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
        tabs=tabs,
        data_type=data_type,
        WebName=current_app.config["TITLE"]
    )

@bp.route("/update_inventory", methods=["POST"])
def update_inventory():
    data = request.get_json()
    inventory_type = data.get("type")
    name = data.get("name")
    values = data.get("values")

    # TODO: Add your logic here (save to DB, file, etc.)
    print(f"Updating {inventory_type} -> {name} with {values}")

    return jsonify({"message": "Inventory updated successfully"}), 200