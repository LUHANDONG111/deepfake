import os
import uuid

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from models import TaskSession, db
from report_analysis import analyze_report
from worker import start_detection_task


api = Blueprint("api", __name__, url_prefix="/api")


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
        video_path=video_path,
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
def status(task_id):
    task = db.session.get(TaskSession, task_id)
    if task is None:
        return jsonify({"status": "error", "message": "task not found"}), 404
    return jsonify({"status": task.status, "progress": task.progress, "error": task.error_message})


@api.get("/result/<task_id>")
def result(task_id):
    task = db.session.get(TaskSession, task_id)
    if task is None:
        return jsonify({"status": "error", "message": "task not found"}), 404
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
