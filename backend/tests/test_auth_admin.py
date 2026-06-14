import os

from app import ensure_first_admin_is_super_admin
from models import TaskSession, User, db
from conftest import auth_header, create_user


def test_login_returns_token_and_user_payload(client, app):
    with app.app_context():
        create_user(username="alice", password="secret123", role="user")

    response = client.post("/api/auth/login", json={"username": "alice", "password": "secret123"})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["token"]
    assert payload["user"]["username"] == "alice"
    assert payload["user"]["role"] == "user"


def test_login_rejects_bad_password_and_inactive_user(client, app):
    with app.app_context():
        create_user(username="alice", password="secret123", is_active=False)

    bad_password = client.post("/api/auth/login", json={"username": "alice", "password": "wrong"})
    inactive = client.post("/api/auth/login", json={"username": "alice", "password": "secret123"})

    assert bad_password.status_code == 401
    assert inactive.status_code == 403


def test_change_password_allows_user_to_login_with_new_password(client, app):
    with app.app_context():
        create_user(username="alice", password="oldpass123")
    headers = auth_header(client, "alice", "oldpass123")

    response = client.post(
        "/api/auth/change-password",
        json={"old_password": "oldpass123", "new_password": "newpass123"},
        headers=headers,
    )
    login = client.post("/api/auth/login", json={"username": "alice", "password": "newpass123"})

    assert response.status_code == 200
    assert login.status_code == 200


def test_user_history_only_includes_own_tasks(client, app):
    with app.app_context():
        alice = create_user(username="alice")
        bob = create_user(username="bob")
        db.session.add(TaskSession(id="task-a", user_id=alice.id, video_path="a.mp4", status="SUCCESS"))
        db.session.add(TaskSession(id="task-b", user_id=bob.id, video_path="b.mp4", status="FAILED"))
        db.session.commit()
    headers = auth_header(client, "alice")

    response = client.get("/api/tasks", headers=headers)

    assert response.status_code == 200
    assert [item["id"] for item in response.get_json()["items"]] == ["task-a"]


def test_user_cannot_access_other_users_task_detail(client, app):
    with app.app_context():
        alice = create_user(username="alice")
        bob = create_user(username="bob")
        db.session.add(TaskSession(id="task-b", user_id=bob.id, video_path="b.mp4", status="SUCCESS"))
        db.session.commit()
    headers = auth_header(client, "alice")

    response = client.get("/api/tasks/task-b", headers=headers)

    assert response.status_code == 403


def test_user_can_update_and_delete_own_task_history(client, app):
    with app.app_context():
        alice = create_user(username="alice")
        video_path = os.path.join(app.config["UPLOAD_FOLDER"], "own-task.mp4")
        report_path = os.path.join(app.config["REPORT_FOLDER"], "own-task.csv")
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        os.makedirs(app.config["REPORT_FOLDER"], exist_ok=True)
        with open(video_path, "wb") as file:
            file.write(b"video")
        with open(report_path, "w", encoding="utf-8") as file:
            file.write("frame_index,timestamp,face_count,raw_score,smoothed_score,verdict,boxes\n")
        db.session.add(TaskSession(id="own-task", user_id=alice.id, video_path=video_path, report_path=report_path, status="FAILED"))
        db.session.commit()
    headers = auth_header(client, "alice")

    updated = client.patch("/api/tasks/own-task", json={"remark": "needs a second review"}, headers=headers)
    deleted = client.delete("/api/tasks/own-task", headers=headers)

    assert updated.status_code == 200
    assert updated.get_json()["task"]["remark"] == "needs a second review"
    assert deleted.status_code == 200
    assert not os.path.exists(video_path)
    assert not os.path.exists(report_path)
    with app.app_context():
        assert db.session.get(TaskSession, "own-task") is None


def test_user_cannot_delete_other_users_task(client, app):
    with app.app_context():
        create_user(username="alice")
        bob = create_user(username="bob")
        db.session.add(TaskSession(id="task-b", user_id=bob.id, video_path="b.mp4", status="SUCCESS"))
        db.session.commit()
    headers = auth_header(client, "alice")

    response = client.delete("/api/tasks/task-b", headers=headers)

    assert response.status_code == 403


def test_admin_can_filter_all_tasks(client, app):
    with app.app_context():
        admin = create_user(username="admin", role="super_admin")
        user = create_user(username="alice")
        db.session.add(TaskSession(id="task-admin", user_id=admin.id, video_path="a.mp4", status="SUCCESS", final_verdict="REAL"))
        db.session.add(TaskSession(id="task-user", user_id=user.id, video_path="b.mp4", status="FAILED", final_verdict="FAKE"))
        db.session.commit()
    headers = auth_header(client, "admin")

    response = client.get("/api/tasks?status=FAILED&verdict=FAKE", headers=headers)
    detail = client.get("/api/tasks/task-user", headers=headers)

    assert response.status_code == 200
    assert [item["id"] for item in response.get_json()["items"]] == ["task-user"]
    assert detail.status_code == 200
    assert detail.get_json()["task"]["id"] == "task-user"


def test_admin_user_management_lifecycle(client, app):
    with app.app_context():
        create_user(username="admin", role="super_admin")
    headers = auth_header(client, "admin")

    created = client.post(
        "/api/admin/users",
        json={"username": "newuser", "password": "password123", "role": "user"},
        headers=headers,
    )
    disabled = client.patch(
        f"/api/admin/users/{created.get_json()['user']['id']}",
        json={"is_active": False},
        headers=headers,
    )
    reset = client.post(
        f"/api/admin/users/{created.get_json()['user']['id']}/reset-password",
        json={"password": "resetpass123"},
        headers=headers,
    )
    login = client.post("/api/auth/login", json={"username": "newuser", "password": "resetpass123"})

    assert created.status_code == 201
    assert disabled.status_code == 200
    assert reset.status_code == 200
    assert login.status_code == 403


def test_admin_can_delete_user_without_deleting_tasks(client, app):
    with app.app_context():
        create_user(username="admin", role="super_admin")
        user = create_user(username="newuser", role="user")
        db.session.add(TaskSession(id="owned-task", user_id=user.id, video_path="owned.mp4", status="FAILED"))
        db.session.commit()
        user_id = user.id
    headers = auth_header(client, "admin")

    response = client.delete(f"/api/admin/users/{user_id}", headers=headers)

    assert response.status_code == 200
    with app.app_context():
        assert db.session.get(User, user_id) is None
        assert db.session.get(TaskSession, "owned-task").user_id is None


def test_admin_cannot_delete_self_or_super_admin(client, app):
    with app.app_context():
        owner = create_user(username="owner", role="super_admin")
        admin = create_user(username="admin", role="admin")
        owner_id = owner.id
        admin_id = admin.id
    admin_headers = auth_header(client, "admin")

    delete_super_admin = client.delete(f"/api/admin/users/{owner_id}", headers=admin_headers)
    delete_self = client.delete(f"/api/admin/users/{admin_id}", headers=admin_headers)

    assert delete_super_admin.status_code == 400
    assert delete_self.status_code == 400


def test_non_admin_cannot_manage_users(client, app):
    with app.app_context():
        create_user(username="alice")
    headers = auth_header(client, "alice")

    response = client.get("/api/admin/users", headers=headers)

    assert response.status_code == 403


def test_admin_delete_task_removes_record_and_files(client, app):
    with app.app_context():
        admin = create_user(username="admin", role="super_admin")
        video_path = os.path.join(app.config["UPLOAD_FOLDER"], "task-1.mp4")
        report_path = os.path.join(app.config["REPORT_FOLDER"], "task-1.csv")
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        os.makedirs(app.config["REPORT_FOLDER"], exist_ok=True)
        with open(video_path, "wb") as file:
            file.write(b"video")
        with open(report_path, "w", encoding="utf-8") as file:
            file.write("frame_index,timestamp,face_count,raw_score,smoothed_score,verdict,boxes\n")
        db.session.add(TaskSession(id="task-1", user_id=admin.id, video_path=video_path, report_path=report_path, status="FAILED"))
        db.session.commit()
    headers = auth_header(client, "admin")

    response = client.delete("/api/admin/tasks/task-1", headers=headers)

    assert response.status_code == 200
    assert not os.path.exists(video_path)
    assert not os.path.exists(report_path)
    with app.app_context():
        assert db.session.get(TaskSession, "task-1") is None


def test_create_app_does_not_create_default_admin(app):
    with app.app_context():
        user_count = User.query.count()

    assert user_count == 0


def test_setup_status_reports_first_run_required(client):
    response = client.get("/api/auth/setup-status")

    assert response.status_code == 200
    assert response.get_json() == {"status": "success", "setup_required": True}


def test_setup_admin_creates_first_admin_and_allows_login(client, app):
    response = client.post(
        "/api/auth/setup-admin",
        json={"username": "owner", "password": "ownerpass123"},
    )
    login = client.post("/api/auth/login", json={"username": "owner", "password": "ownerpass123"})

    assert response.status_code == 201
    assert response.get_json()["user"]["role"] == "super_admin"
    assert login.status_code == 200
    with app.app_context():
        assert User.query.count() == 1


def test_setup_admin_is_closed_after_any_user_exists(client, app):
    with app.app_context():
        create_user(username="admin", role="super_admin")

    response = client.post(
        "/api/auth/setup-admin",
        json={"username": "owner", "password": "ownerpass123"},
    )

    assert response.status_code == 409


def test_setup_status_requires_setup_when_users_exist_but_no_admin(client, app):
    with app.app_context():
        create_user(username="alice", password="password123", role="user")

    response = client.get("/api/auth/setup-status")

    assert response.status_code == 200
    assert response.get_json() == {"status": "success", "setup_required": True}


def test_setup_admin_promotes_existing_user_when_no_admin_exists(client, app):
    with app.app_context():
        create_user(username="alice", password="password123", role="user")

    response = client.post(
        "/api/auth/setup-admin",
        json={"username": "alice", "password": "password123"},
    )
    login = client.post("/api/auth/login", json={"username": "alice", "password": "password123"})

    assert response.status_code == 200
    assert response.get_json()["user"]["role"] == "super_admin"
    assert login.status_code == 200
    assert login.get_json()["user"]["role"] == "super_admin"


def test_super_admin_cannot_lower_own_role_or_disable_self(client, app):
    with app.app_context():
        super_admin = create_user(username="owner", password="ownerpass123", role="super_admin")
        super_admin_id = super_admin.id
    headers = auth_header(client, "owner", "ownerpass123")

    lower_role = client.patch(
        f"/api/admin/users/{super_admin_id}",
        json={"role": "admin"},
        headers=headers,
    )
    disable_self = client.patch(
        f"/api/admin/users/{super_admin_id}",
        json={"is_active": False},
        headers=headers,
    )

    assert lower_role.status_code == 400
    assert disable_self.status_code == 400
    with app.app_context():
        user = db.session.get(User, super_admin_id)
        assert user.role == "super_admin"
        assert user.is_active is True


def test_existing_first_admin_is_promoted_to_super_admin(app):
    with app.app_context():
        first_admin = create_user(username="first-admin", role="admin", is_active=False)
        second_admin = create_user(username="second-admin", role="super_admin")

        ensure_first_admin_is_super_admin()

        assert db.session.get(User, first_admin.id).role == "super_admin"
        assert db.session.get(User, first_admin.id).is_active is True
        assert db.session.get(User, second_admin.id).role == "admin"
