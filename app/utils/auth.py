import os
from functools import wraps
from flask import session, redirect, url_for, request
from werkzeug.security import check_password_hash, generate_password_hash


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin.login", next=request.url))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get("admin_logged_in"):
                return redirect(url_for("admin.login", next=request.url))
            user_role = session.get("admin_role", "viewer")
            if user_role not in roles and user_role != "superadmin":
                from flask import abort
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator


def check_admin_credentials(username: str, password: str):
    """
    Returns (ok, role) or (False, None).
    First tries AdminUser table, falls back to env vars.
    """
    from app.models import AdminUser
    from app import db

    user = AdminUser.query.filter_by(username=username, is_active=True).first()
    if user and check_password_hash(user.password_hash, password):
        return True, user.role

    # Fallback env (bootstrap)
    expected_user = os.getenv("ADMIN_USERNAME", "admin")
    expected_pass = os.getenv("ADMIN_PASSWORD", "admin123")
    if username == expected_user and password == expected_pass:
        return True, "superadmin"

    return False, None


def hash_password(password: str) -> str:
    return generate_password_hash(password)
