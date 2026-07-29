import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH", 10 * 1024 * 1024))
    # Uploads OUTSIDE static — not publicly browsable
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    upload_dir = os.getenv("UPLOAD_FOLDER") or os.path.join(basedir, "uploads")
    app.config["UPLOAD_FOLDER"] = upload_dir
    app.config["WTF_CSRF_ENABLED"] = True
    app.config["WTF_CSRF_TIME_LIMIT"] = 3600

    turso_url = os.getenv("TURSO_DATABASE_URL")
    turso_token = os.getenv("TURSO_AUTH_TOKEN")

    if turso_url and turso_token:
        app.config["SQLALCHEMY_DATABASE_URI"] = f"{turso_url}?authToken={turso_token}"
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "connect_args": {"check_same_thread": False},
            "pool_pre_ping": True,
        }
    else:
        db_path = os.path.join(basedir, "imei.db")
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)

    from app.routes.public import public_bp
    from app.routes.admin import admin_bp
    from app.routes.contact import contact_bp
    from app.routes.files import files_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(contact_bp)
    app.register_blueprint(files_bp)

    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        from flask import render_template
        return render_template("errors/500.html"), 500

    @app.errorhandler(403)
    def forbidden(e):
        from flask import render_template
        return render_template("errors/403.html"), 403

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    return app
