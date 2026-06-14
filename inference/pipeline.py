import csv
import json
from dataclasses import dataclass

from inference.alignment import align_face
from inference.smoothing import SlidingWindowSmoother
from inference.video import OpenCVVideoReader


@dataclass
class FrameReportRow:
    frame_index: int
    timestamp: float
    face_count: int
    raw_score: float
    smoothed_score: float
    verdict: str
    boxes: list[list[int]]


@dataclass
class DetectionResult:
    final_score: float
    final_verdict: str
    rows: list[FrameReportRow]


class DetectionPipeline:
    def __init__(self, detector, classifier, video_reader_factory=OpenCVVideoReader):
        self.detector = detector
        self.classifier = classifier
        self.video_reader_factory = video_reader_factory

    def run(self, video_path, report_path, threshold, window_size, skip_rate, progress_callback=None):
        reader = self.video_reader_factory(video_path)
        if reader is None:
            raise ValueError("Unable to read video")

        smoother = SlidingWindowSmoother(window_size)
        rows = []

        try:
            total_frames = getattr(reader, "total_frames", 0)
            fps = getattr(reader, "fps", 0.0) or 0.0
            if total_frames <= 0:
                raise ValueError("Unable to read video: total frame count is zero")

            for frame_index, frame in reader:
                if frame_index % max(1, int(skip_rate)) != 0:
                    continue

                detections = self.detector.detect(frame)
                if not detections:
                    _progress(progress_callback, frame_index, total_frames)
                    continue

                frame_score = self._score_frame(frame, detections)
                smoothed_score = smoother.add(frame_score)
                rows.append(
                    FrameReportRow(
                        frame_index=frame_index,
                        timestamp=(frame_index / fps) if fps > 0 else 0.0,
                        face_count=len(detections),
                        raw_score=frame_score,
                        smoothed_score=smoothed_score,
                        verdict="FAKE" if smoothed_score >= threshold else "REAL",
                        boxes=_extract_boxes(detections),
                    )
                )
                _progress(progress_callback, frame_index, total_frames)
        finally:
            reader.release()

        final_score = sum(row.smoothed_score for row in rows) / len(rows) if rows else 0.0
        final_verdict = "FAKE" if final_score >= threshold else "REAL"
        self._write_report(report_path, rows)
        return DetectionResult(final_score=final_score, final_verdict=final_verdict, rows=rows)

    def _score_frame(self, frame, detections):
        scores = []
        for detection in detections:
            face_image = align_face(frame, detection)
            scores.append(float(self.classifier.predict_fake_probability(face_image)))
        return max(scores)

    def _write_report(self, report_path, rows):
        with open(report_path, "w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["frame_index", "timestamp", "face_count", "raw_score", "smoothed_score", "verdict", "boxes"])
            for row in rows:
                writer.writerow(
                    [
                        row.frame_index,
                        f"{row.timestamp:.4f}",
                        row.face_count,
                        f"{row.raw_score:.6f}",
                        f"{row.smoothed_score:.6f}",
                        row.verdict,
                        json.dumps(row.boxes),
                    ]
                )


def _progress(callback, frame_index, total_frames):
    if callback is None:
        return
    callback(int(((frame_index + 1) / max(1, total_frames)) * 100))


def _extract_boxes(detections):
    boxes = []
    for detection in detections:
        box = detection.get("box")
        if box and len(box) == 4:
            boxes.append([int(value) for value in box])
    return boxes
