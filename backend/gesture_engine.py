"""Stable, confidence-scored hand gesture recognition for the ordering kiosk."""
from collections import deque
from math import hypot

from .config import (
    FINGER_EXTENSION_MARGIN,
    FIST_CANCEL_HOLD_SECONDS,
    GESTURE_COOLDOWN_SECONDS,
    PINCH_DISTANCE_THRESHOLD,
    SWIPE_MIN_DURATION,
    SWIPE_RELEASE_THRESHOLD,
    SWIPE_X_THRESHOLD,
    SWIPE_Y_THRESHOLD,
)


class GestureEngine:
    """Classify MediaPipe hand landmarks and debounce deliberate actions."""

    def __init__(self):
        self.samples = deque(maxlen=6)
        self.last_event = 0.0
        self.candidate = None
        self.candidate_frames = 0
        self.pinch_since = None
        self.pinch_fired = False
        self.fist_since = None
        self.fist_fired = False
        self.motion_fired = False
        self.detected = "no_hand"
        self.confidence = 0.0

    @staticmethod
    def _extended(points, tip, pip):
        return points[tip][1] < points[pip][1] - FINGER_EXTENSION_MARGIN

    @staticmethod
    def _clip(value, low=0.0, high=0.98):
        return max(low, min(high, value))

    def describe(self, points):
        """Return the current gesture name and a heuristic confidence score."""
        if not isinstance(points, (list, tuple)) or len(points) < 21:
            return "no_hand", 0.0

        index, middle, ring, pinky = (
            self._extended(points, tip, pip)
            for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18))
        )
        extended = (index, middle, ring, pinky)
        curled_count = sum(not value for value in extended)
        pinch_distance = hypot(points[4][0] - points[8][0], points[4][1] - points[8][1])
        palm_width = hypot(points[5][0] - points[17][0], points[5][1] - points[17][1])
        pinch_ratio = pinch_distance / palm_width if palm_width > 0.08 else 1.0
        thumb_up = points[4][1] < points[3][1] - 0.035
        thumb_down = points[4][1] > points[3][1] + 0.035

        if palm_width > 0.08 and pinch_ratio < PINCH_DISTANCE_THRESHOLD:
            name = "pinch"
            confidence = self._clip(0.68 + (PINCH_DISTANCE_THRESHOLD - pinch_ratio) * 0.8)
        elif curled_count == 4:
            name, confidence = "fist", 0.82
        elif thumb_up and curled_count >= 3:
            name, confidence = "thumbs_up", 0.82
        elif thumb_down and curled_count >= 3:
            name, confidence = "thumbs_down", 0.82
        elif all(extended):
            name = "open_palm"
            confidence = self._clip(0.66 + sum(max(0, points[p][1] - points[t][1]) for t, p in ((8, 6), (12, 10), (16, 14), (20, 18))) * 0.8)
        elif index and middle and not ring and not pinky:
            name, confidence = "two_fingers", 0.84
        elif index and not middle and not ring and not pinky:
            name, confidence = "one_finger", 0.82
        else:
            name, confidence = "hand", 0.52
        return name, confidence

    def update(self, points, now):
        """Return one debounced command, while keeping current detection metadata."""
        if not isinstance(points, (list, tuple)) or len(points) < 21:
            self.samples.clear()
            self.candidate = None
            self.candidate_frames = 0
            self.pinch_since = None
            self.pinch_fired = False
            self.fist_since = None
            self.fist_fired = False
            self.motion_fired = False
            self.detected, self.confidence = "no_hand", 0.0
            return None

        name, confidence = self.describe(points)
        self.detected, self.confidence = name, confidence
        self.samples.append((now, points[9][0], points[9][1]))

        if name == self.candidate:
            self.candidate_frames += 1
        else:
            self.candidate = name
            self.candidate_frames = 1

        # Pinch confirms checkout after a deliberate hold. A held fist cancels
        # the current customer step; it never clears the cart or submits an order.
        if name == "pinch":
            self.fist_since = None
            self.fist_fired = False
            self.pinch_since = self.pinch_since or now
            if now - self.pinch_since >= 1.15 and not self.pinch_fired:
                self.pinch_fired = True
                return self._emit("confirm", now)
            return None
        if self.pinch_since is not None:
            self.pinch_since = None
            self.pinch_fired = False

        if name == "fist":
            self.fist_since = self.fist_since or now
            if now - self.fist_since >= FIST_CANCEL_HOLD_SECONDS and not self.fist_fired:
                self.fist_fired = True
                return self._emit("cancel", now)
            return None
        if self.fist_since is not None:
            self.fist_since = None
            self.fist_fired = False

        if now - self.last_event < GESTURE_COOLDOWN_SECONDS or self.candidate_frames < 3:
            return None

        # Detect movement before held poses. A downward swipe can briefly look
        # like a thumbs-down as the hand rotates; clear movement should scroll,
        # never trigger the destructive thumbs-down action.
        if len(self.samples) >= 4 and name in (
            "one_finger", "hand", "open_palm", "thumbs_up", "thumbs_down", "fist"
        ):
            old, current = self.samples[0], self.samples[-1]
            dx, dy = current[1] - old[1], current[2] - old[2]
            elapsed = current[0] - old[0]
            if elapsed >= SWIPE_MIN_DURATION:
                if abs(dx) < SWIPE_RELEASE_THRESHOLD and abs(dy) < SWIPE_RELEASE_THRESHOLD:
                    self.motion_fired = False
                if not self.motion_fired and abs(dx) > SWIPE_X_THRESHOLD and abs(dx) > abs(dy) * 1.12:
                    self.motion_fired = True
                    return self._emit("next" if dx < 0 else "previous", now)
                if not self.motion_fired and abs(dy) > SWIPE_Y_THRESHOLD and abs(dy) > abs(dx) * 1.12:
                    self.motion_fired = True
                    return self._emit("scroll_up" if dy < 0 else "scroll_down", now)

        return None

    def _emit(self, command, now):
        self.last_event = now
        self.samples.clear()
        return command
