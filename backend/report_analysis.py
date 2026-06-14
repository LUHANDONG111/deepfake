import csv
import json
import os


def empty_analysis():
    return {
        "summary": {
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
        },
        "timeline": [],
        "risk_segments": [],
    }


def analyze_report(report_path, risk_limit=5):
    if not report_path or not os.path.exists(report_path):
        return empty_analysis()

    rows = []
    with open(report_path, "r", encoding="utf-8", newline="") as file:
        for raw_row in csv.DictReader(file):
            row = _parse_row(raw_row)
            if row is not None:
                rows.append(row)

    if not rows:
        return empty_analysis()

    fake_frames = sum(1 for row in rows if row["verdict"] == "FAKE")
    real_frames = sum(1 for row in rows if row["verdict"] == "REAL")
    sampled_frames = len(rows)
    highest_risk = max(rows, key=lambda row: row["smoothed_score"])

    return {
        "summary": {
            "sampled_frames": sampled_frames,
            "face_frames": sum(1 for row in rows if row["face_count"] > 0),
            "fake_frames": fake_frames,
            "real_frames": real_frames,
            "fake_ratio": fake_frames / sampled_frames,
            "real_ratio": real_frames / sampled_frames,
            "max_raw_score": max(row["raw_score"] for row in rows),
            "max_smoothed_score": highest_risk["smoothed_score"],
            "highest_risk_time": highest_risk["timestamp"],
            "highest_risk_frame": highest_risk["frame_index"],
        },
        "timeline": rows,
        "risk_segments": sorted(rows, key=lambda row: row["smoothed_score"], reverse=True)[:risk_limit],
    }


def _parse_row(row):
    try:
        return {
            "frame_index": int(row["frame_index"]),
            "timestamp": float(row["timestamp"]),
            "face_count": int(row["face_count"]),
            "raw_score": float(row["raw_score"]),
            "smoothed_score": float(row["smoothed_score"]),
            "verdict": str(row["verdict"]).strip().upper(),
            "boxes": _parse_boxes(row.get("boxes")),
        }
    except (KeyError, TypeError, ValueError):
        return None


def _parse_boxes(value):
    if not value:
        return []

    try:
        raw_boxes = json.loads(value)
    except (TypeError, ValueError):
        return []

    boxes = []
    if not isinstance(raw_boxes, list):
        return boxes

    for box in raw_boxes:
        if isinstance(box, list) and len(box) == 4:
            try:
                boxes.append([int(coordinate) for coordinate in box])
            except (TypeError, ValueError):
                continue
    return boxes
