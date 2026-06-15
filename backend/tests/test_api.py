import io
import os

from models import TaskSession, db
from conftest import auth_header, create_user


def test_upload_rejects_non_mp4_file(client):
    create_user()
    headers = auth_header(client)
    response = client.post(
        "/api/upload",
        data={
            "file": (io.BytesIO(b"not video"), "sample.txt"),
            "threshold": "0.5",
            "window_size": "5",
            "skip_rate": "2",
        },
        content_type="multipart/form-data",
        headers=headers,
    )

    assert response.status_code == 400
    assert response.get_json()["status"] == "error"


def test_upload_creates_pending_task_without_starting_worker(client, app):
    with app.app_context():
        user = create_user()
        user_id = user.id
    headers = auth_header(client)

    response = client.post(
        "/api/upload",
        data={
            "file": (io.BytesIO(b"fake mp4 bytes"), "sample video.mp4"),
            "threshold": "0.6",
            "window_size": "7",
            "skip_rate": "3",
        },
        content_type="multipart/form-data",
        headers=headers,
    )

    assert response.status_code == 202
    payload = response.get_json()
    assert payload["status"] == "success"

    with app.app_context():
        task = db.session.get(TaskSession, payload["task_id"])
        assert task is not None
        assert task.status == "PENDING"
        assert task.user_id == user_id
        assert task.threshold == 0.6
        assert task.window_size == 7
        assert task.skip_rate == 3
        assert task.original_filename == "sample_video.mp4"
        assert os.path.exists(task.video_path)


def test_status_returns_404_for_missing_task(client):
    create_user()
    headers = auth_header(client)

    response = client.get("/api/status/missing-task", headers=headers)

    assert response.status_code == 404
    assert response.get_json()["status"] == "error"


def test_status_includes_failure_error(client, app):
    with app.app_context():
        user = create_user()
        task = TaskSession(id="task-1", user_id=user.id, video_path="video.mp4", status="FAILED", progress=20, error_message="bad video")
        db.session.add(task)
        db.session.commit()
    headers = auth_header(client)

    response = client.get("/api/status/task-1", headers=headers)

    assert response.status_code == 200
    assert response.get_json() == {"status": "FAILED", "progress": 20, "error": "bad video"}


def test_result_returns_success_payload(client, app):
    with app.app_context():
        user = create_user()
        task = TaskSession(
            id="task-2",
            user_id=user.id,
            video_path=os.path.join(app.config["UPLOAD_FOLDER"], "task-2.mp4"),
            report_path=os.path.join(app.config["REPORT_FOLDER"], "task-2.csv"),
            status="SUCCESS",
            progress=100,
            final_score=0.7842,
            final_verdict="FAKE",
        )
        db.session.add(task)
        db.session.commit()
    headers = auth_header(client)

    response = client.get("/api/result/task-2", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["task_id"] == "task-2"
    assert payload["status"] == "SUCCESS"
    assert payload["final_verdict"] == "FAKE"
    assert payload["final_score"] == 0.7842
    assert payload["video_url"] == "/static/uploads/task-2.mp4"
    assert payload["report_url"] == "/static/reports/task-2.csv"


def test_result_includes_audit_data_from_csv(client, app):
    report_path = os.path.join(app.config["REPORT_FOLDER"], "task-3.csv")
    os.makedirs(app.config["REPORT_FOLDER"], exist_ok=True)
    with open(report_path, "w", encoding="utf-8", newline="") as file:
        file.write("frame_index,timestamp,face_count,raw_score,smoothed_score,verdict,boxes\n")
        file.write('0,0.0000,1,0.300000,0.300000,REAL,"[[10, 10, 60, 60]]"\n')
        file.write('2,0.0800,2,0.900000,0.600000,FAKE,"[[10, 10, 60, 60], [20, 20, 70, 70]]"\n')
        file.write('4,0.1600,1,0.700000,0.800000,FAKE,"[[14, 14, 64, 64]]"\n')

    with app.app_context():
        user = create_user()
        task = TaskSession(
            id="task-3",
            user_id=user.id,
            video_path=os.path.join(app.config["UPLOAD_FOLDER"], "task-3.mp4"),
            report_path=report_path,
            status="SUCCESS",
            progress=100,
            final_score=0.5667,
            final_verdict="FAKE",
            threshold=0.55,
            window_size=7,
            skip_rate=3,
        )
        db.session.add(task)
        db.session.commit()
    headers = auth_header(client)

    response = client.get("/api/result/task-3", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["config"] == {"threshold": 0.55, "window_size": 7, "skip_rate": 3}
    assert payload["summary"] == {
        "sampled_frames": 3,
        "face_frames": 3,
        "fake_frames": 2,
        "real_frames": 1,
        "fake_ratio": 2 / 3,
        "real_ratio": 1 / 3,
        "max_raw_score": 0.9,
        "max_smoothed_score": 0.8,
        "highest_risk_time": 0.16,
        "highest_risk_frame": 4,
    }
    assert payload["timeline"] == [
        {
            "frame_index": 0,
            "timestamp": 0.0,
            "face_count": 1,
            "raw_score": 0.3,
            "smoothed_score": 0.3,
            "verdict": "REAL",
            "boxes": [[10, 10, 60, 60]],
        },
        {
            "frame_index": 2,
            "timestamp": 0.08,
            "face_count": 2,
            "raw_score": 0.9,
            "smoothed_score": 0.6,
            "verdict": "FAKE",
            "boxes": [[10, 10, 60, 60], [20, 20, 70, 70]],
        },
        {
            "frame_index": 4,
            "timestamp": 0.16,
            "face_count": 1,
            "raw_score": 0.7,
            "smoothed_score": 0.8,
            "verdict": "FAKE",
            "boxes": [[14, 14, 64, 64]],
        },
    ]
    assert payload["risk_segments"][0] == {
        "frame_index": 4,
        "timestamp": 0.16,
        "face_count": 1,
        "raw_score": 0.7,
        "smoothed_score": 0.8,
        "verdict": "FAKE",
        "boxes": [[14, 14, 64, 64]],
    }


def test_result_tolerates_missing_csv(client, app):
    with app.app_context():
        user = create_user()
        task = TaskSession(
            id="task-4",
            user_id=user.id,
            video_path=os.path.join(app.config["UPLOAD_FOLDER"], "task-4.mp4"),
            report_path=os.path.join(app.config["REPORT_FOLDER"], "missing.csv"),
            status="SUCCESS",
            progress=100,
            final_score=0.1,
            final_verdict="REAL",
        )
        db.session.add(task)
        db.session.commit()
    headers = auth_header(client)

    response = client.get("/api/result/task-4", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["timeline"] == []
    assert payload["risk_segments"] == []
    assert payload["summary"] == {
        "sampled_frames": 0,
        "face_frames": 0,
        "fake_frames": 0,
        "real_frames": 0,
        "fake_ratio": 0.0,
        "real_ratio": 0.0,
        "max_raw_score": 0.0,
        "max_smoothed_score": 0.0,
        "highest_risk_time": None,
        "highest_risk_frame": None,
    }


def test_result_keeps_core_payload_compatible(client, app):
    with app.app_context():
        user = create_user()
        task = TaskSession(
            id="task-5",
            user_id=user.id,
            video_path=os.path.join(app.config["UPLOAD_FOLDER"], "task-5.mp4"),
            report_path=os.path.join(app.config["REPORT_FOLDER"], "task-5.csv"),
            status="SUCCESS",
            progress=100,
            final_score=0.7842,
            final_verdict="FAKE",
        )
        db.session.add(task)
        db.session.commit()
    headers = auth_header(client)

    response = client.get("/api/result/task-5", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    core_payload = {
        key: payload[key]
        for key in ("task_id", "status", "final_verdict", "final_score", "video_url", "report_url")
    }
    assert core_payload == {
        "task_id": "task-5",
        "status": "SUCCESS",
        "final_verdict": "FAKE",
        "final_score": 0.7842,
        "video_url": "/static/uploads/task-5.mp4",
        "report_url": "/static/reports/task-5.csv",
    }


def test_task_payloads_include_original_filename(client, app):
    with app.app_context():
        user = create_user()
        task = TaskSession(
            id="task-6",
            user_id=user.id,
            video_path=os.path.join(app.config["UPLOAD_FOLDER"], "task-6.mp4"),
            status="FAILED",
            original_filename="interview.mp4",
        )
        db.session.add(task)
        db.session.commit()
    headers = auth_header(client)

    list_response = client.get("/api/tasks", headers=headers)
    detail_response = client.get("/api/tasks/task-6", headers=headers)

    assert list_response.status_code == 200
    assert list_response.get_json()["items"][0]["original_filename"] == "interview.mp4"
    assert detail_response.status_code == 200
    assert detail_response.get_json()["task"]["original_filename"] == "interview.mp4"
