from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class TaskSession(db.Model):
    __tablename__ = "task_sessions"

    id = db.Column(db.String(36), primary_key=True)
    video_path = db.Column(db.String(512), nullable=False)
    report_path = db.Column(db.String(512), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="PENDING")
    progress = db.Column(db.Integer, nullable=False, default=0)
    final_score = db.Column(db.Float, nullable=True)
    final_verdict = db.Column(db.String(10), nullable=True)
    error_message = db.Column(db.String(1024), nullable=True)
    threshold = db.Column(db.Float, nullable=False, default=0.5)
    window_size = db.Column(db.Integer, nullable=False, default=5)
    skip_rate = db.Column(db.Integer, nullable=False, default=2)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
