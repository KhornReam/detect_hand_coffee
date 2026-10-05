"""Single-admin password authentication and signed, HttpOnly browser sessions."""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path
from threading import Lock
from fastapi import HTTPException, Request
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
SECRET_FILE = ROOT / "data" / "admin_signing.key"
COOKIE_NAME = "brew_admin_session"
SESSION_SECONDS = 8 * 60 * 60
_key_lock = Lock()
_attempts = {}

def admin_email():
    load_dotenv(ROOT / ".env", override=True)
    return os.environ.get("KIOSK_ADMIN_EMAIL", "").strip().casefold()

def admin_configured():
    load_dotenv(ROOT / ".env", override=True)
    return bool(admin_email() and os.environ.get("KIOSK_ADMIN_PASSWORD"))

def _signing_key():
    configured = os.environ.get("KIOSK_SECRET_KEY", "")
    if configured:
        if len(configured.encode("utf-8")) < 32:
            raise RuntimeError("KIOSK_SECRET_KEY must contain at least 32 bytes")
        return configured.encode("utf-8")
    with _key_lock:
        SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            return SECRET_FILE.read_bytes()
        except FileNotFoundError:
            key = secrets.token_bytes(32)
            try:
                with SECRET_FILE.open("xb") as f:
                    f.write(key)
                return key
            except FileExistsError:
                return SECRET_FILE.read_bytes()

def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

def _password_digest(password: str, email: str) -> bytes:
    salt = hashlib.sha256(("brew-co-admin:" + email).encode("utf-8")).digest()
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)

def verify_credentials(email: str, password: str) -> bool:
    load_dotenv(ROOT / ".env", override=True)
    target = admin_email()
    configured_password = os.environ.get("KIOSK_ADMIN_PASSWORD", "")
    if not target or not configured_password:
        return False
    email_ok = hmac.compare_digest(email.strip().casefold().encode(), target.encode())
    entered = _password_digest(password, target)
    expected = _password_digest(configured_password, target)
    return email_ok and hmac.compare_digest(entered, expected)

def create_session(email: str) -> str:
    now = int(time.time())
    body = _b64(json.dumps({"sub": email.casefold(), "iat": now, "exp": now + SESSION_SECONDS},
                           separators=(",", ":")).encode("utf-8"))
    signature = _b64(hmac.new(_signing_key(), body.encode("ascii"), hashlib.sha256).digest())
    return body + "." + signature

def session_email(token: str | None):
    if not token or "." not in token:
        return None
    body, signature = token.rsplit(".", 1)
    expected = _b64(hmac.new(_signing_key(), body.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if payload.get("exp", 0) <= time.time() or payload.get("sub") != admin_email():
            return None
        return payload["sub"]
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None

def require_admin(request: Request):
    if not admin_configured():
        raise HTTPException(status_code=503, detail="Admin login is not configured. Set KIOSK_ADMIN_EMAIL and KIOSK_ADMIN_PASSWORD.")
    email = session_email(request.cookies.get(COOKIE_NAME))
    if not email:
        raise HTTPException(status_code=401, detail="Admin login required")
    return email

def allow_login_attempt(client_ip: str) -> bool:
    now = time.time()
    attempts = [stamp for stamp in _attempts.get(client_ip, []) if now - stamp < 300]
    if len(attempts) >= 8:
        _attempts[client_ip] = attempts
        return False
    attempts.append(now)
    _attempts[client_ip] = attempts
    return True

def clear_login_attempts(client_ip: str):
    _attempts.pop(client_ip, None)
