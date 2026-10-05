import os
import cv2
from .config import HAND_DETECTION_CONFIDENCE, HAND_TRACKING_CONFIDENCE

class HandTracker:
    """Capture local camera frames; hand tracking is optional when MediaPipe cannot load."""
    def __init__(self, camera_index=0):
        self.capture = self._open_camera(camera_index) if camera_index is not None else None
        if self.capture is not None:
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.detector = None
        self.tracking_error = None
        try:
            import mediapipe as mp
            self.mp_hands = mp.solutions.hands
            self.detector = self.mp_hands.Hands(static_image_mode=False, max_num_hands=1,
                        model_complexity=0, min_detection_confidence=HAND_DETECTION_CONFIDENCE,
                        min_tracking_confidence=HAND_TRACKING_CONFIDENCE)
        except Exception as exc:
            self.mp_hands = None
            self.tracking_error = f"{type(exc).__name__}: {exc}"

    @staticmethod
    def _open_camera(camera_index):
        backends = (cv2.CAP_MSMF, cv2.CAP_DSHOW) if os.name == "nt" else (cv2.CAP_ANY,)
        for backend in backends:
            capture = cv2.VideoCapture(camera_index, backend)
            if capture.isOpened():
                return capture
            capture.release()
        return cv2.VideoCapture(camera_index)

    def read(self):
        if self.capture is None:
            return None, None
        ok, frame = self.capture.read()
        if not ok:
            return None, None
        frame = cv2.flip(frame, 1)
        return self.process(frame)

    def process(self, frame):
        if frame is None:
            return None, None
        if self.detector is None:
            return frame, None
        results = self.detector.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if not results.multi_hand_landmarks:
            return frame, None
        points = results.multi_hand_landmarks[0].landmark
        return frame, [(p.x, p.y) for p in points]

    def close(self):
        if self.capture is not None:
            self.capture.release()
        if self.detector is not None:
            self.detector.close()
