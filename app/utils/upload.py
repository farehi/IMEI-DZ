import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf", "webp"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file, prefix: str = "file") -> tuple:
    """Save file outside public static. Returns (stored_name, original_name) or (None, None)."""
    if not file or not file.filename:
        return None, None
    if not allowed_file(file.filename):
        return None, None

    ext = file.filename.rsplit(".", 1)[1].lower()
    original = secure_filename(file.filename)[:200]
    unique_name = f"{prefix}_{uuid.uuid4().hex[:16]}.{ext}"

    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, unique_name)
    file.save(filepath)
    return unique_name, original


def delete_file(filename: str) -> bool:
    if not filename:
        return False
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    if os.path.isfile(path):
        os.remove(path)
        return True
    return False


def get_file_path(filename: str):
    if not filename:
        return None
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    if os.path.isfile(path):
        return path
    return None
