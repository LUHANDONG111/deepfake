import os
import tempfile

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from models import User, db


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


def create_user(username="user1", password="password123", role="user", is_active=True):
    user = User.query.filter_by(username=username).first()
    if user is None:
        user = User(username=username)
        db.session.add(user)
    user.password_hash = generate_password_hash(password)
    user.role = role
    user.is_active = is_active
    db.session.commit()
    return user


def auth_header(client, username="user1", password="password123"):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.get_json()["token"]
    return {"Authorization": f"Bearer {token}"}
