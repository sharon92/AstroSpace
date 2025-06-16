import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
)
from werkzeug.security import check_password_hash, generate_password_hash

from AstroSpace.db import get_conn

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_conn()
        error = None

        with db.cursor() as cur:
            cur.execute(
                "SELECT * FROM users")
            existing_users = cur.fetchall()
        if len(existing_users) >= current_app.config['MAX_USERS']:
            error = 'Sorry maximum number of users reached :('
        
        else:
            if not username:
                error = 'Username is required.'
            elif not password:
                error = 'Password is required.'

            if error is None:
                try:
                    with db.cursor() as cur:
                        cur.execute(
                            "INSERT INTO users (username, password) VALUES (%s, %s)",
                            (username, generate_password_hash(password)),
                        )
                    db.commit()
                except db.IntegrityError:
                    error = f"User {username} is already registered."
                else:
                    return redirect(url_for("auth.login"))

        flash(error)

    return render_template('auth/auth.html', title='Register', WebName = current_app.config["TITLE"])

@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_conn()
        error = None
        with db.cursor() as cur:
            cur.execute(
                "SELECT * FROM users WHERE username = %s", (username,) )
            user = cur.fetchone()
        
        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('index'))

        flash(error)

    return render_template('auth/auth.html', title='Log In', WebName = current_app.config["TITLE"])

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        cur = get_conn().cursor()
        cur.execute(
            "SELECT * FROM users WHERE id = %s", (user_id,)
        )
        g.user = cur.fetchone()

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view