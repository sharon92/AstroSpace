from flask import abort, g


def current_user_is_admin():
    return bool(getattr(g, "user", None) and g.user.get("admin"))


def require_admin():
    if not current_user_is_admin():
        abort(403)


def require_owner(username):
    if current_user_is_admin():
        return

    if not getattr(g, "user", None) or g.user.get("username") != username:
        abort(403)
