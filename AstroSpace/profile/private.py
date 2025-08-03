# private profile - what the user can see and edit
from flask import Blueprint, render_template, current_app, g
from AstroSpace.db import get_conn
from AstroSpace.auth import login_required

bp = Blueprint("my_profile", __name__, url_prefix="/my_profile")

@bp.route("/profile")
@login_required
def profile():

    db = get_conn()
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, title, created_at FROM images WHERE author = %s ORDER BY created_at DESC",
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
            cur.execute(
                f"SELECT * FROM {item}",
            )
            values = cur.fetchall()
            inventory_dict[item] = {}
            for obj in values:
                inventory_dict[item][obj["name"]] = obj

    return render_template(
        "profile.html",
        posts=posts,
        inventory=inventory_dict,
        tabs=tabs,
        WebName=current_app.config["TITLE"]
    )

