# private profile - what the user can see and edit
from flask import g
from flask import Blueprint, render_template, current_app
from AstroSpace.utils.queries import get_conn
from flask_login import login_required

bp = Blueprint("profile", __name__, url_prefix="/profile")