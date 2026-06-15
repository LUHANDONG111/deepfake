from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    tasks = db.relationship("TaskSession", back_populates="user", lazy=True)


class TaskSession(db.Model):
    __tablename__ = "task_sessions"

    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    video_path = db.Column(db.String(512), nullable=False)
    original_filename = db.Column(db.String(255), nullable=True)
    report_path = db.Column(db.String(512), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="PENDING")
    progress = db.Column(db.Integer, nullable=False, default=0)
    final_score = db.Column(db.Float, nullable=True)
    final_verdict = db.Column(db.String(10), nullable=True)
    error_message = db.Column(db.String(1024), nullable=True)
    remark = db.Column(db.String(500), nullable=True)
    threshold = db.Column(db.Float, nullable=False, default=0.5)
    window_size = db.Column(db.Integer, nullable=False, default=5)
    skip_rate = db.Column(db.Integer, nullable=False, default=2)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", back_populates="tasks")
