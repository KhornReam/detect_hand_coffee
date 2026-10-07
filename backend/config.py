from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "orders.sqlite3"
MENU_PATH = DATA_DIR / "menu.json"
load_dotenv(ROOT / ".env")
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "coffee_sell")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
GESTURE_HOLD_SECONDS = 1.25
FIST_CANCEL_HOLD_SECONDS = 0.65
GESTURE_COOLDOWN_SECONDS = 0.28
# Ratio of thumb/index tip distance to palm width, so pinches behave similarly
# whether the hand is near or far from the webcam.
PINCH_DISTANCE_THRESHOLD = 0.38
FINGER_EXTENSION_MARGIN = 0.025
OPEN_PALM_HOLD_SECONDS = 0.45
THUMBS_UP_HOLD_SECONDS = 0.55
SWIPE_X_THRESHOLD = 0.12
SWIPE_Y_THRESHOLD = 0.12
SWIPE_MIN_DURATION = 0.12
SWIPE_RELEASE_THRESHOLD = 0.04
HAND_DETECTION_CONFIDENCE = 0.65
HAND_TRACKING_CONFIDENCE = 0.55
