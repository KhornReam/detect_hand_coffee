"""Store customer contact form messages in MySQL."""
import re
from datetime import datetime, timezone

from .database import connect

EMAIL_RE = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")


def save_message(name, email, subject, message):
    name = str(name or "").strip()
    email = str(email or "").strip().casefold()
    subject = str(subject or "").strip()
    message = str(message or "").strip()
    if not name or len(name) > 120:
        raise ValueError("Enter your name (up to 120 characters)")
    if len(email) > 254 or not EMAIL_RE.fullmatch(email):
        raise ValueError("Enter a valid email address")
    if len(subject) > 160:
        raise ValueError("Subject is too long")
    if not message or len(message) > 5000:
        raise ValueError("Message must be between 1 and 5000 characters")
    created = datetime.now(timezone.utc).isoformat()
    db = connect()
    try:
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO contact_messages (name,email,subject,message,created_at) VALUES (%s,%s,%s,%s,%s)",
            (name, email, subject, message, created),
        )
        db.commit()
        return {"ok": True, "id": cursor.lastrowid}
    finally:
        db.close()


def list_messages():
    db = connect()
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT id,name,email,subject,message,created_at AS createdAt "
            "FROM contact_messages ORDER BY id DESC LIMIT 200"
        )
        return cursor.fetchall()
    finally:
        db.close()
