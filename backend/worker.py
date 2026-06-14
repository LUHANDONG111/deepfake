import threading

from inference.detector import OpenCVFaceDetector
from inference.classifier import build_classifier
from inference.pipeline import DetectionPipeline
from models import TaskSession, db


def start_detection_task(app, task_id):
    thread = threading.Thread(target=run_detection_task, args=(app, task_id), daemon=True)
    thread.start()
    return thread


def run_detection_task(app, task_id):
    with app.app_context():
        task = db.session.get(TaskSession, task_id)
        if task is None:
            return

        task.status = "PROCESSING"
        task.progress = 1
        db.session.commit()

        try:
            pipeline = create_detection_pipeline(app.config.get("MODEL_PATH"))
            result = pipeline.run(
                video_path=task.video_path,
                report_path=task.report_path,
                threshold=task.threshold,
                window_size=task.window_size,
                skip_rate=task.skip_rate,
                progress_callback=lambda value: _update_progress(task_id, value),
            )
            task = db.session.get(TaskSession, task_id)
            task.status = "SUCCESS"
            task.progress = 100
            task.final_score = result.final_score
            task.final_verdict = result.final_verdict
            task.error_message = None
            db.session.commit()
        except Exception as exc:
            task = db.session.get(TaskSession, task_id)
            task.status = "FAILED"
            task.error_message = str(exc)
            task.progress = min(task.progress or 0, 99)
            db.session.commit()


def _update_progress(task_id, value):
    task = db.session.get(TaskSession, task_id)
    if task is None or task.status == "FAILED":
        return
    task.progress = max(1, min(99, int(value)))
    db.session.commit()


def create_detection_pipeline(model_path=None):
    return DetectionPipeline(detector=OpenCVFaceDetector(), classifier=build_classifier(model_path))
