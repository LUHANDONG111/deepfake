import os


BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'deepfake.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(BASE_DIR, "static", "uploads"))
    REPORT_FOLDER = os.environ.get("REPORT_FOLDER", os.path.join(BASE_DIR, "static", "reports"))
    MODEL_PATH = os.environ.get("MODEL_PATH", os.path.join(BASE_DIR, "best_model.pth"))
    MAX_CONTENT_LENGTH = 1024 * 1024 * 1024
    START_BACKGROUND_WORKERS = True
    FACE_CASCADE_PATH = os.environ.get("FACE_CASCADE_PATH")
