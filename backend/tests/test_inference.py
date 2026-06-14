import csv
import json
import os

import numpy as np
import pytest

from inference.alignment import align_face
from inference.classifier import HeuristicClassifier, XceptionClassifier, build_classifier
from inference.pipeline import DetectionPipeline
from inference.smoothing import SlidingWindowSmoother


class FakeVideoReader:
    def __init__(self, frames, fps=25.0):
        self.frames = frames
        self.total_frames = len(frames)
        self.fps = fps

    def __iter__(self):
        for index, frame in enumerate(self.frames):
            yield index, frame

    def release(self):
        pass


class FakeFaceDetector:
    def __init__(self, faces_by_frame):
        self.faces_by_frame = faces_by_frame

    def detect(self, frame):
        frame_id = int(frame[0, 0, 0])
        return self.faces_by_frame.get(frame_id, [])


class RecordingClassifier:
    def __init__(self, scores):
        self.scores = list(scores)
        self.calls = 0

    def predict_fake_probability(self, face_image):
        self.calls += 1
        return self.scores.pop(0)


def frame(value):
    return np.full((80, 80, 3), value, dtype=np.uint8)


def face():
    return {
        "box": [10, 10, 60, 60],
        "landmarks": {
            "left_eye": [24, 28],
            "right_eye": [46, 28],
            "nose": [35, 38],
            "mouth_left": [26, 50],
            "mouth_right": [44, 50],
        },
    }


def face_with_box(box):
    detection = face()
    detection["box"] = box
    return detection


def test_sliding_window_smoother_averages_recent_values_only():
    smoother = SlidingWindowSmoother(window_size=3)

    assert smoother.add(0.2) == pytest.approx(0.2)
    assert smoother.add(0.4) == pytest.approx(0.3)
    assert smoother.add(0.8) == pytest.approx(0.466666, rel=1e-5)
    assert smoother.add(1.0) == pytest.approx(0.733333, rel=1e-5)


def test_align_face_returns_standardized_crop():
    image = frame(100)

    aligned = align_face(image, face(), output_size=(299, 299))

    assert aligned.shape == (299, 299, 3)
    assert aligned.dtype == np.uint8


def test_pipeline_skips_frames_without_running_classifier(tmp_path):
    reader = FakeVideoReader([frame(0), frame(1), frame(2), frame(3)])
    detector = FakeFaceDetector({0: [face()], 2: [face()]})
    classifier = RecordingClassifier([0.2, 0.8])
    pipeline = DetectionPipeline(detector=detector, classifier=classifier, video_reader_factory=lambda _: reader)

    result = pipeline.run(
        video_path="video.mp4",
        report_path=os.path.join(tmp_path, "report.csv"),
        threshold=0.5,
        window_size=2,
        skip_rate=2,
    )

    assert classifier.calls == 2
    assert result.final_score == pytest.approx(0.35)
    assert result.final_verdict == "REAL"
    assert [row.frame_index for row in result.rows] == [0, 2]
    assert result.rows[0].boxes == [[10, 10, 60, 60]]


def test_pipeline_uses_highest_face_score_per_frame(tmp_path):
    reader = FakeVideoReader([frame(0)])
    detector = FakeFaceDetector({0: [face_with_box([10, 10, 60, 60]), face_with_box([20, 20, 70, 70])]})
    classifier = RecordingClassifier([0.3, 0.9])
    pipeline = DetectionPipeline(detector=detector, classifier=classifier, video_reader_factory=lambda _: reader)

    result = pipeline.run(
        video_path="video.mp4",
        report_path=os.path.join(tmp_path, "report.csv"),
        threshold=0.5,
        window_size=5,
        skip_rate=1,
    )

    assert classifier.calls == 2
    assert result.rows[0].raw_score == pytest.approx(0.9)
    assert result.rows[0].boxes == [[10, 10, 60, 60], [20, 20, 70, 70]]
    assert result.final_score == pytest.approx(0.9)
    assert result.final_verdict == "FAKE"


def test_pipeline_writes_face_boxes_to_report_csv(tmp_path):
    report_path = os.path.join(tmp_path, "report.csv")
    reader = FakeVideoReader([frame(0)])
    detector = FakeFaceDetector({0: [face_with_box([10, 10, 60, 60]), face_with_box([20, 20, 70, 70])]})
    classifier = RecordingClassifier([0.3, 0.9])
    pipeline = DetectionPipeline(detector=detector, classifier=classifier, video_reader_factory=lambda _: reader)

    pipeline.run(
        video_path="video.mp4",
        report_path=report_path,
        threshold=0.5,
        window_size=5,
        skip_rate=1,
    )

    with open(report_path, "r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert "boxes" in rows[0]
    assert json.loads(rows[0]["boxes"]) == [[10, 10, 60, 60], [20, 20, 70, 70]]


def test_pipeline_fails_for_unreadable_video(tmp_path):
    pipeline = DetectionPipeline(detector=FakeFaceDetector({}), classifier=RecordingClassifier([]), video_reader_factory=lambda _: None)

    with pytest.raises(ValueError, match="Unable to read video"):
        pipeline.run(
            video_path="broken.mp4",
            report_path=os.path.join(tmp_path, "report.csv"),
            threshold=0.5,
            window_size=5,
            skip_rate=1,
        )


def test_heuristic_classifier_returns_probability_range():
    classifier = HeuristicClassifier()
    score = classifier.predict_fake_probability(np.zeros((299, 299, 3), dtype=np.uint8))

    assert 0.0 <= score <= 1.0


def test_build_classifier_uses_xception_when_model_path_exists(tmp_path, monkeypatch):
    model_path = tmp_path / "best_model.pth"
    model_path.write_bytes(b"placeholder")

    class FakeXceptionClassifier:
        def __init__(self, received_path):
            self.received_path = received_path

    monkeypatch.setattr("inference.classifier.XceptionClassifier", FakeXceptionClassifier)

    classifier = build_classifier(str(model_path))

    assert isinstance(classifier, FakeXceptionClassifier)
    assert classifier.received_path == str(model_path)


def test_xception_classifier_reports_missing_weight_file():
    with pytest.raises(FileNotFoundError, match="Model weights not found"):
        XceptionClassifier("missing-model.pth")
