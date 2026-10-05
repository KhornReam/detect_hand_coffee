import asyncio
import base64
import cv2
import time
from .hand_tracker import HandTracker
from .gesture_engine import GestureEngine

async def stream_gestures():
    tracker = HandTracker()
    engine = GestureEngine()
    tracking_available = tracker.detector is not None
    try:
        while True:
            frame, landmarks = await asyncio.to_thread(tracker.read)
            if frame is None:
                yield {"type":"status", "camera":"disconnected", "tracking":False, "trackingAvailable":tracking_available}
                await asyncio.sleep(1)
                continue
            event = engine.update(landmarks, time.monotonic())
            preview = None
            if tracker.capture.isOpened():
                small = cv2.resize(frame, (320, 240))
                ok, encoded = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 55])
                if ok: preview = base64.b64encode(encoded).decode("ascii")
            if event:
                yield {"type":"gesture", "gesture":event, "detected":engine.detected, "confidence":engine.confidence, "camera":"connected", "tracking":True, "trackingAvailable":tracking_available, "preview":preview}
            else:
                yield {"type":"status", "camera":"connected", "tracking":bool(landmarks), "detected":engine.detected, "confidence":engine.confidence, "trackingAvailable":tracking_available, "preview":preview}
            await asyncio.sleep(.12)
    finally:
        tracker.close()
