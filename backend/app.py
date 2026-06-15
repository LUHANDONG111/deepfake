import os

from flask import Flask, jsonify, request
from sqlalchemy import inspect, text

from config import Config
from models import TaskSession, User, db
from routes import api

try:
    from flask_migrate import Migrate
except ImportError:
    Migrate = None


migrate = Migrate() if Migrate else None


def create_app(test_config=None):
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["REPORT_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)

    db.init_app(app)
    if migrate:
        migrate.init_app(app, db)
    app.register_blueprint(api)

    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
        return response

    @app.get("/")
    def index():
        return jsonify({"status": "ok", "message": "Deepfake detection API"})

    with app.app_context():
        run_sqlite_compat_migrations()
        db.create_all()
        ensure_first_admin_is_super_admin()

    return app


def run_sqlite_compat_migrations():
    inspector = inspect(db.engine)
    if "task_sessions" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("task_sessions")}
    if "user_id" not in columns:
        db.session.execute(text("ALTER TABLE task_sessions ADD COLUMN user_id INTEGER"))
        db.session.commit()
    if "remark" not in columns:
        db.session.execute(text("ALTER TABLE task_sessions ADD COLUMN remark VARCHAR(500)"))
        db.session.commit()
    if "original_filename" not in columns:
        db.session.execute(text("ALTER TABLE task_sessions ADD COLUMN original_filename VARCHAR(255)"))
        db.session.commit()


def assign_legacy_tasks_to_admin():
    admin = User.query.filter(User.role.in_(("super_admin", "admin"))).order_by(User.created_at.asc()).first()
    if admin is None:
        return
    TaskSession.query.filter(TaskSession.user_id.is_(None)).update({"user_id": admin.id})
    db.session.commit()


def ensure_first_admin_is_super_admin():
    first_admin = User.query.filter(User.role.in_(("super_admin", "admin"))).order_by(User.created_at.asc()).first()
    if first_admin is None:
        return
    changed = False
    if first_admin.role != "super_admin":
        first_admin.role = "super_admin"
        changed = True
    if not first_admin.is_active:
        first_admin.is_active = True
        changed = True
    extra_super_admins = User.query.filter(User.role == "super_admin", User.id != first_admin.id).all()
    for user in extra_super_admins:
        user.role = "admin"
        changed = True
    if not changed:
        return
    db.session.commit()


if __name__ == "__main__":
    create_app().run(debug=True, threaded=True)
