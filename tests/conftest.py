import os
import tempfile

import pytest

from app import create_app
from models import db


@pytest.fixture()
def app():
    temp_dir = tempfile.TemporaryDirectory()
    upload_dir = os.path.join(temp_dir.name, "uploads")
    report_dir = os.path.join(temp_dir.name, "reports")

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{os.path.join(temp_dir.name, 'test.db')}",
            "UPLOAD_FOLDER": upload_dir,
            "REPORT_FOLDER": report_dir,
            "SERVER_NAME": "localhost",
            "START_BACKGROUND_WORKERS": False,
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
        db.engine.dispose()

    temp_dir.cleanup()


@pytest.fixture()
def client(app):
    return app.test_client()
