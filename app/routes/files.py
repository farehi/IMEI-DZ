"""Protected file serving — uploads are outside static."""
from flask import Blueprint, send_file, abort, session
from app.utils.upload import get_file_path
from app.utils.auth import login_required

files_bp = Blueprint("files", __name__)


@files_bp.route("/files/<path:filename>")
@login_required
def serve_upload(filename):
    """Only logged-in admins can download uploaded files."""
    # Prevent path traversal
    if ".." in filename or filename.startswith("/"):
        abort(404)
    path = get_file_path(filename)
    if not path:
        abort(404)
    return send_file(path, as_attachment=False)
