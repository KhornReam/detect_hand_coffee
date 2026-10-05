"""Customer account registration, password verification, and signed sessions."""
import base64
import hashlib
import hmac
import json
import re
import secrets
import time
from datetime import datetime, timezone

from fastapi import HTTPException, Request
from mysql.connector import IntegrityError

from .admin_auth import _signing_key
from .database import connect

COOKIE_NAME = "brew_customer_session"
SESSION_SECONDS = 30 * 24 * 60 * 60
EMAIL_RE = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")


def _b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _password_hash(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    return f"pbkdf2_sha256${_b64(salt)}${_b64(digest)}"


def _verify_password(password, encoded):
    try:
        algorithm, salt, expected = encoded.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        salt_bytes = base64.urlsafe_b64decode(salt + "=" * (-len(salt) % 4))
        expected_bytes = base64.urlsafe_b64decode(expected + "=" * (-len(expected) % 4))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, 310_000)
        return hmac.compare_digest(actual, expected_bytes)
    except (ValueError, TypeError):
        return False


def _clean(name, email, password):
    name = str(name or "").strip()
    email = str(email or "").strip().casefold()
    password = str(password or "")
    if not name or len(name) > 120:
        raise ValueError("Enter your name (up to 120 characters)")
    if len(email) > 254 or not EMAIL_RE.fullmatch(email):
        raise ValueError("Enter a valid email address")
    if len(password) < 8 or len(password) > 256:
        raise ValueError("Password must be between 8 and 256 characters")
    return name, email, password


def register(name, email, password):
    name, email, password = _clean(name, email, password)
    created = datetime.now(timezone.utc).isoformat()
    db = connect()
    try:
        cursor = db.cursor()
        try:
            cursor.execute(
                "INSERT INTO customer_accounts (name,email,password_hash,created_at) VALUES (%s,%s,%s,%s)",
                (name, email, _password_hash(password), created),
            )
            customer_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO customer_records (name,email,phone,created_at) VALUES (%s,%s,'',%s) "
                "ON DUPLICATE KEY UPDATE name=VALUES(name)",
                (name, email, created),
            )
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("An account with this email already exists. Please sign in.") from exc
        return {"id": customer_id, "name": name, "email": email}
    finally:
        db.close()


def authenticate(email, password):
    email = str(email or "").strip().casefold()
    if len(email) > 254 or not EMAIL_RE.fullmatch(email) or not password:
        return None
    db = connect()
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id,name,email,password_hash FROM customer_accounts WHERE email=%s", (email,))
        user = cursor.fetchone()
        if not user or not _verify_password(str(password), user["password_hash"]):
            return None
        return {"id": user["id"], "name": user["name"], "email": user["email"]}
    finally:
        db.close()


def create_session(user):
    now = int(time.time())
    body = _b64(json.dumps({"sub": user["email"], "uid": user["id"], "iat": now,
                            "exp": now + SESSION_SECONDS}, separators=(",", ":")).encode())
    signature = _b64(hmac.new(_signing_key(), body.encode("ascii"), hashlib.sha256).digest())
    return body + "." + signature


def session_user(token):
    if not token or "." not in token:
        return None
    body, signature = token.rsplit(".", 1)
    expected = _b64(hmac.new(_signing_key(), body.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if payload.get("exp", 0) <= time.time() or not payload.get("uid"):
            return None
        return {"id": int(payload["uid"]), "email": payload["sub"]}
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def require_customer(request: Request):
    user = session_user(request.cookies.get(COOKIE_NAME))
    if not user:
        raise HTTPException(status_code=401, detail="Customer sign in required")
    return user
