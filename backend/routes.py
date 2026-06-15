import os
import uuid

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from auth import admin_required, create_token, current_user, hash_password, login_required, user_payload, verify_password
from models import TaskSession, User, db
from report_analysis import analyze_report
from worker import start_detection_task


api = Blueprint("api", __name__, url_prefix="/api")


@api.get("/auth/setup-status")
def setup_status():
    return jsonify({"status": "success", "setup_required": _admin_count() == 0})


@api.post("/auth/setup-admin")
def setup_admin():
    if _admin_count() > 0:
        return jsonify({"status": "error", "message": "setup is already complete"}), 409

    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    if not username:
        return jsonify({"status": "error", "message": "username is required"}), 400
    if len(password) < 8:
        return jsonify({"status": "error", "message": "password must be at least 8 characters"}), 400

    user = User.query.filter_by(username=username).first()
    status_code = 200
    if user is None:
        user = User(username=username, password_hash=hash_password(password), role="super_admin", is_active=True)
        db.session.add(user)
        status_code = 201
    else:
        if not verify_password(user, password):
            return jsonify({"status": "error", "message": "invalid username or password"}), 401
        user.role = "super_admin"
        user.is_active = True

    db.session.commit()
    _assign_legacy_tasks_to_admin(user)
    return jsonify({"status": "success", "user": user_payload(user)}), status_code


@api.post("/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    user = User.query.filter_by(username=username).first()
    if user is None or not verify_password(user, password):
        return jsonify({"status": "error", "message": "invalid username or password"}), 401
    if not user.is_active:
        return jsonify({"status": "error", "message": "user is disabled"}), 403
    return jsonify({"status": "success", "token": create_token(user), "user": user_payload(user)})


@api.get("/auth/me")
@login_required
def me():
    return jsonify({"status": "success", "user": user_payload(current_user())})


@api.post("/auth/change-password")
@login_required
def change_password():
    payload = request.get_json(silent=True) or {}
    old_password = str(payload.get("old_password", ""))
    new_password = str(payload.get("new_password", ""))
    if not verify_password(current_user(), old_password):
        return jsonify({"status": "error", "message": "old password is incorrect"}), 400
    if len(new_password) < 8:
        return jsonify({"status": "error", "message": "new password must be at least 8 characters"}), 400
    current_user().password_hash = hash_password(new_password)
    db.session.commit()
    return jsonify({"status": "success"})


def _parse_float(name, default, min_value, max_value):
    raw = request.form.get(name, default)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number")
    if value < min_value or value > max_value:
        raise ValueError(f"{name} must be between {min_value} and {max_value}")
    return value


def _parse_int(name, default, min_value, max_value):
    raw = request.form.get(name, default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be an integer")
    if value < min_value or value > max_value:
        raise ValueError(f"{name} must be between {min_value} and {max_value}")
    return value


@api.post("/upload")
@login_required
def upload():
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"status": "error", "message": "file is required"}), 400

    filename = secure_filename(file.filename)
    if not filename.lower().endswith(".mp4"):
        return jsonify({"status": "error", "message": "only .mp4 files are supported"}), 400

    try:
        threshold = _parse_float("threshold", 0.5, 0.0, 1.0)
        window_size = _parse_int("window_size", 5, 1, 120)
        skip_rate = _parse_int("skip_rate", 2, 1, 120)
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400

    task_id = str(uuid.uuid4())
    stored_name = f"{task_id}.mp4"
    video_path = os.path.join(current_app.config["UPLOAD_FOLDER"], stored_name)
    report_path = os.path.join(current_app.config["REPORT_FOLDER"], f"{task_id}.csv")
    file.save(video_path)

    task = TaskSession(
        id=task_id,
        user_id=current_user().id,
        video_path=video_path,
        original_filename=filename,
        report_path=report_path,
        status="PENDING",
        threshold=threshold,
        window_size=window_size,
        skip_rate=skip_rate,
    )
    db.session.add(task)
    db.session.commit()

    if current_app.config.get("START_BACKGROUND_WORKERS", True):
        start_detection_task(current_app._get_current_object(), task_id)

    return jsonify({"status": "success", "task_id": task_id}), 202


@api.get("/status/<task_id>")
@login_required
def status(task_id):
    task = db.session.get(TaskSession, task_id)
    if task is None:
        return jsonify({"status": "error", "message": "task not found"}), 404
    if not _can_access_task(task):
        return jsonify({"status": "error", "message": "permission denied"}), 403
    return jsonify({"status": task.status, "progress": task.progress, "error": task.error_message})


@api.get("/result/<task_id>")
@login_required
def result(task_id):
    task = db.session.get(TaskSession, task_id)
    if task is None:
        return jsonify({"status": "error", "message": "task not found"}), 404
    if not _can_access_task(task):
        return jsonify({"status": "error", "message": "permission denied"}), 403
    if task.status != "SUCCESS":
        return jsonify({"status": task.status, "error": task.error_message}), 409

    report_analysis = analyze_report(task.report_path)
    return jsonify(
        {
            "task_id": task.id,
            "status": task.status,
            "final_verdict": task.final_verdict,
            "final_score": task.final_score,
            "video_url": f"/static/uploads/{os.path.basename(task.video_path)}",
            "report_url": f"/static/reports/{os.path.basename(task.report_path)}",
            "config": {
                "threshold": task.threshold,
                "window_size": task.window_size,
                "skip_rate": task.skip_rate,
            },
            "summary": report_analysis["summary"],
            "timeline": report_analysis["timeline"],
            "risk_segments": report_analysis["risk_segments"],
        }
    )


@api.get("/tasks")
@login_required
def list_tasks():
    query = TaskSession.query
    user = current_user()
    if user.role not in {"admin", "super_admin"}:
        query = query.filter(TaskSession.user_id == user.id)
    else:
        user_id = request.args.get("user_id")
        if user_id:
            query = query.filter(TaskSession.user_id == int(user_id))

    status_filter = request.args.get("status")
    verdict_filter = request.args.get("verdict")
    if status_filter:
        query = query.filter(TaskSession.status == status_filter)
    if verdict_filter:
        query = query.filter(TaskSession.final_verdict == verdict_filter)

    tasks = query.order_by(TaskSession.created_at.desc()).all()
    return jsonify({"status": "success", "total": len(tasks), "items": [_task_payload(task) for task in tasks]})


@api.get("/tasks/<task_id>")
@login_required
def task_detail(task_id):
    task = db.session.get(TaskSession, task_id)
    if task is None:
        return jsonify({"status": "error", "message": "task not found"}), 404
    if not _can_access_task(task):
        return jsonify({"status": "error", "message": "permission denied"}), 403
    payload = _task_payload(task)
    if task.status == "SUCCESS":
        payload["result"] = _result_payload(task)
    return jsonify({"status": "success", "task": payload})


@api.patch("/tasks/<task_id>")
@login_required
def update_task(task_id):
    task = db.session.get(TaskSession, task_id)
    if task is None:
        return jsonify({"status": "error", "message": "task not found"}), 404
    if not _can_access_task(task):
        return jsonify({"status": "error", "message": "permission denied"}), 403
    payload = request.get_json(silent=True) or {}
    if "remark" in payload:
        remark = str(payload.get("remark") or "").strip()
        if len(remark) > 500:
            return jsonify({"status": "error", "message": "remark must be 500 characters or fewer"}), 400
        task.remark = remark or None
    db.session.commit()
    return jsonify({"status": "success", "task": _task_payload(task)})


@api.delete("/tasks/<task_id>")
@login_required
def delete_task(task_id):
    task = db.session.get(TaskSession, task_id)
    if task is None:
        return jsonify({"status": "error", "message": "task not found"}), 404
    if not _can_access_task(task):
        return jsonify({"status": "error", "message": "permission denied"}), 403
    _delete_task_record(task)
    return jsonify({"status": "success"})


@api.get("/admin/users")
@admin_required
def admin_list_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({"status": "success", "items": [user_payload(user) for user in users]})


@api.post("/admin/users")
@admin_required
def admin_create_user():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    role = str(payload.get("role", "user")).strip()
    if not username:
        return jsonify({"status": "error", "message": "username is required"}), 400
    if len(password) < 8:
        return jsonify({"status": "error", "message": "password must be at least 8 characters"}), 400
    if role not in {"admin", "user"}:
        return jsonify({"status": "error", "message": "role must be admin or user"}), 400
    if User.query.filter_by(username=username).first() is not None:
        return jsonify({"status": "error", "message": "username already exists"}), 409

    user = User(username=username, password_hash=hash_password(password), role=role, is_active=True)
    db.session.add(user)
    db.session.commit()
    return jsonify({"status": "success", "user": user_payload(user)}), 201


@api.patch("/admin/users/<int:user_id>")
@admin_required
def admin_update_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"status": "error", "message": "user not found"}), 404
    payload = request.get_json(silent=True) or {}
    if "role" in payload:
        role = str(payload["role"]).strip()
        if role not in {"admin", "user"}:
            return jsonify({"status": "error", "message": "role must be admin or user"}), 400
        if user.id == current_user().id and user.role == "super_admin" and role != "super_admin":
            return jsonify({"status": "error", "message": "super admin cannot lower own role"}), 400
        user.role = role
    if "is_active" in payload:
        if user.id == current_user().id and user.role == "super_admin" and not bool(payload["is_active"]):
            return jsonify({"status": "error", "message": "super admin cannot disable self"}), 400
        user.is_active = bool(payload["is_active"])
    db.session.commit()
    return jsonify({"status": "success", "user": user_payload(user)})


@api.post("/admin/users/<int:user_id>/reset-password")
@admin_required
def admin_reset_password(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"status": "error", "message": "user not found"}), 404
    payload = request.get_json(silent=True) or {}
    password = str(payload.get("password", ""))
    if len(password) < 8:
        return jsonify({"status": "error", "message": "password must be at least 8 characters"}), 400
    user.password_hash = hash_password(password)
    db.session.commit()
    return jsonify({"status": "success"})


@api.delete("/admin/users/<int:user_id>")
@admin_required
def admin_delete_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"status": "error", "message": "user not found"}), 404
    if user.id == current_user().id:
        return jsonify({"status": "error", "message": "cannot delete current user"}), 400
    if user.role == "super_admin":
        return jsonify({"status": "error", "message": "cannot delete super admin"}), 400
    TaskSession.query.filter(TaskSession.user_id == user.id).update({"user_id": None})
    db.session.delete(user)
    db.session.commit()
    return jsonify({"status": "success"})


@api.delete("/admin/tasks/<task_id>")
@admin_required
def admin_delete_task(task_id):
    task = db.session.get(TaskSession, task_id)
    if task is None:
        return jsonify({"status": "error", "message": "task not found"}), 404
    _delete_task_record(task)
    return jsonify({"status": "success"})


def _delete_task_record(task):
    for path in (task.video_path, task.report_path):
        if path and os.path.exists(path):
            os.remove(path)
    db.session.delete(task)
    db.session.commit()


def _can_access_task(task):
    user = current_user()
    return user.role in {"admin", "super_admin"} or task.user_id == user.id


def _assign_legacy_tasks_to_admin(admin):
    TaskSession.query.filter(TaskSession.user_id.is_(None)).update({"user_id": admin.id})
    db.session.commit()


def _admin_count():
    return User.query.filter(User.role.in_(("admin", "super_admin")), User.is_active.is_(True)).count()


def _task_payload(task):
    return {
        "id": task.id,
        "user_id": task.user_id,
        "username": task.user.username if task.user else None,
        "original_filename": task.original_filename,
        "status": task.status,
        "progress": task.progress,
        "final_score": task.final_score,
        "final_verdict": task.final_verdict,
        "error_message": task.error_message,
        "remark": task.remark,
        "threshold": task.threshold,
        "window_size": task.window_size,
        "skip_rate": task.skip_rate,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


def _result_payload(task):
    report_analysis = analyze_report(task.report_path)
    return {
        "task_id": task.id,
        "status": task.status,
        "final_verdict": task.final_verdict,
        "final_score": task.final_score,
        "video_url": f"/static/uploads/{os.path.basename(task.video_path)}",
        "report_url": f"/static/reports/{os.path.basename(task.report_path)}",
        "config": {
            "threshold": task.threshold,
            "window_size": task.window_size,
            "skip_rate": task.skip_rate,
        },
        "summary": report_analysis["summary"],
        "timeline": report_analysis["timeline"],
        "risk_segments": report_analysis["risk_segments"],
    }
