import cv2


class OpenCVVideoReader:
    def __init__(self, video_path):
        self.capture = cv2.VideoCapture(video_path)
        if not self.capture.isOpened():
            raise ValueError("Unable to read video")
        self.total_frames = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = float(self.capture.get(cv2.CAP_PROP_FPS) or 0.0)
        if self.total_frames <= 0:
            self.capture.release()
            raise ValueError("Unable to read video: total frame count is zero")

    def __iter__(self):
        index = 0
        while True:
            ok, frame = self.capture.read()
            if not ok:
                break
            yield index, frame
            index += 1

    def release(self):
        self.capture.release()
