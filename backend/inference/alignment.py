import math

import cv2
import numpy as np


def align_face(frame, detection, output_size=(299, 299)):
    landmarks = detection.get("landmarks") or {}
    box = detection.get("box")
    if not box:
        raise ValueError("face detection is missing a bounding box")

    x1, y1, x2, y2 = [int(v) for v in box]
    h, w = frame.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)

    if x2 <= x1 or y2 <= y1:
        raise ValueError("face detection has an invalid bounding box")

    left_eye = landmarks.get("left_eye")
    right_eye = landmarks.get("right_eye")
    aligned = frame

    if left_eye and right_eye:
        lx, ly = left_eye
        rx, ry = right_eye
        center = ((float(lx) + float(rx)) / 2.0, (float(ly) + float(ry)) / 2.0)
        angle = math.degrees(math.atan2(float(ry) - float(ly), float(rx) - float(lx)))
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        aligned = cv2.warpAffine(frame, matrix, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

    crop = aligned[y1:y2, x1:x2]
    if crop.size == 0:
        raise ValueError("aligned face crop is empty")
    return cv2.resize(crop, output_size, interpolation=cv2.INTER_AREA)
