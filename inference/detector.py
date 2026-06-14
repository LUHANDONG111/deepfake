import cv2


class OpenCVFaceDetector:
    def __init__(self, cascade_path=None):
        self.cascade_path = cascade_path or cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.classifier = cv2.CascadeClassifier(self.cascade_path)
        if self.classifier.empty():
            raise ValueError(f"Unable to load face cascade: {self.cascade_path}")

    def detect(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.classifier.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
        detections = []
        for x, y, w, h in faces:
            x1, y1, x2, y2 = int(x), int(y), int(x + w), int(y + h)
            detections.append(
                {
                    "box": [x1, y1, x2, y2],
                    "landmarks": _estimate_landmarks(x1, y1, w, h),
                }
            )
        return detections


def _estimate_landmarks(x, y, w, h):
    return {
        "left_eye": [int(x + w * 0.33), int(y + h * 0.38)],
        "right_eye": [int(x + w * 0.67), int(y + h * 0.38)],
        "nose": [int(x + w * 0.50), int(y + h * 0.55)],
        "mouth_left": [int(x + w * 0.38), int(y + h * 0.75)],
        "mouth_right": [int(x + w * 0.62), int(y + h * 0.75)],
    }
