from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, Response, Depends
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .database import initialize, database_health
from .menu_manager import get_menu, save_menu
from .order_manager import place_order, list_orders, update_status
from .cart_manager import validate_items
from .customer_manager import list_customers, create_customer, update_customer, delete_customer
from .customer_auth import (COOKIE_NAME as CUSTOMER_COOKIE, SESSION_SECONDS as CUSTOMER_SESSION_SECONDS,
                            authenticate as authenticate_customer, create_session as create_customer_session,
                            register as register_customer, require_customer)
from .contact_manager import save_message, list_messages
from .admin_auth import (COOKIE_NAME, SESSION_SECONDS, admin_configured, admin_email,
                         allow_login_attempt, clear_login_attempts, create_session,
                         require_admin, verify_credentials)

ROOT = Path(__file__).resolve().parent.parent

@asynccontextmanager
async def lifespan(_app):
    initialize()
    yield

app = FastAPI(title="Brew & Co. Kiosk", version="1.0.0", lifespan=lifespan)

@app.middleware("http")
async def avoid_stale_kiosk_assets(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.startswith(("/js/", "/css/")) or path.endswith(".html"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response

class OrderInput(BaseModel):
    idempotencyKey: str = Field(min_length=8, max_length=100)
    items: list[dict]

class StatusInput(BaseModel):
    status: str

class AdminLoginInput(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)

class CustomerInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    phone: str = Field(default="", max_length=40)

class ContactInput(BaseModel):
    name: str = Field(default="Brew & Co.", max_length=120)
    email: str = Field(default="", max_length=254)
    phone: str = Field(default="", max_length=40)
    address: str = Field(default="", max_length=240)
    hours: str = Field(default="", max_length=160)
    website: str = Field(default="", max_length=240)

class CustomerRegisterInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=256)

class CustomerLoginInput(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)

class ContactMessageInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    subject: str = Field(default="", max_length=160)
    message: str = Field(min_length=1, max_length=5000)

@app.get("/api/health")
def health():
    try:
        return {"status": "ok", **database_health()}
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))

@app.post("/api/admin/login")
def admin_login(body: AdminLoginInput, request: Request, response: Response):
    ip = request.client.host if request.client else "unknown"
    if not allow_login_attempt(ip):
        raise HTTPException(429, "Too many sign-in attempts. Wait five minutes and try again.")
    if not admin_configured():
        raise HTTPException(503, "Admin login is not configured. Set KIOSK_ADMIN_EMAIL and KIOSK_ADMIN_PASSWORD.")
    if not verify_credentials(body.email, body.password):
        raise HTTPException(401, "Email or password is incorrect")
    clear_login_attempts(ip)
    response.set_cookie(COOKIE_NAME, create_session(admin_email()), httponly=True,
                        secure=request.url.scheme == "https", samesite="strict",
                        max_age=SESSION_SECONDS, path="/")
    return {"email": admin_email(), "expiresIn": SESSION_SECONDS}

@app.get("/api/admin/session")
def admin_session(email: str = Depends(require_admin)):
    return {"email": email}

@app.post("/api/admin/logout")
def admin_logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="strict")
    return {"ok": True}

@app.post("/api/customer/register", status_code=201)
def customer_register(body: CustomerRegisterInput, request: Request, response: Response):
    ip = request.client.host if request.client else "unknown"
    if not allow_login_attempt("customer:" + ip):
        raise HTTPException(429, "Too many attempts. Wait five minutes and try again.")
    try:
        user = register_customer(body.name, body.email, body.password)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))
    clear_login_attempts("customer:" + ip)
    response.set_cookie(CUSTOMER_COOKIE, create_customer_session(user), httponly=True,
                        secure=request.url.scheme == "https", samesite="lax",
                        max_age=CUSTOMER_SESSION_SECONDS, path="/")
    return user

@app.post("/api/customer/login")
def customer_login(body: CustomerLoginInput, request: Request, response: Response):
    ip = request.client.host if request.client else "unknown"
    if not allow_login_attempt("customer:" + ip):
        raise HTTPException(429, "Too many sign-in attempts. Wait five minutes and try again.")
    try:
        user = authenticate_customer(body.email, body.password)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))
    if not user:
        raise HTTPException(401, "Email or password is incorrect")
    clear_login_attempts("customer:" + ip)
    response.set_cookie(CUSTOMER_COOKIE, create_customer_session(user), httponly=True,
                        secure=request.url.scheme == "https", samesite="lax",
                        max_age=CUSTOMER_SESSION_SECONDS, path="/")
    return user

@app.get("/api/customer/session")
def customer_session(user: dict = Depends(require_customer)):
    # Resolve the display name from the account record after verifying the signed cookie.
    from .database import connect
    db = connect()
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id,name,email FROM customer_accounts WHERE id=%s", (user["id"],))
        account = cursor.fetchone()
        if not account:
            raise HTTPException(401, "Customer account no longer exists")
        return account
    finally:
        db.close()

@app.post("/api/customer/logout")
def customer_logout(response: Response):
    response.delete_cookie(CUSTOMER_COOKIE, path="/", httponly=True, samesite="lax")
    return {"ok": True}

@app.post("/api/contact")
def contact_message(body: ContactMessageInput):
    try:
        return save_message(body.name, body.email, body.subject, body.message)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))

@app.get("/api/admin/messages")
def admin_contact_messages(_email: str = Depends(require_admin)):
    try:
        return list_messages()
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))

@app.get("/api/menu")
def menu():
    try: return get_menu()
    except (OSError, ValueError) as exc: raise HTTPException(500, str(exc))

@app.get("/api/admin/menu")
def admin_menu(_email: str = Depends(require_admin)):
    try: return get_menu()
    except (OSError, ValueError) as exc: raise HTTPException(500, str(exc))

@app.put("/api/admin/menu")
def update_menu(body: dict, _email: str = Depends(require_admin)):
    try: return save_menu(body)
    except ValueError as exc: raise HTTPException(400, str(exc))

@app.get("/api/admin/contact")
def admin_contact(_email: str = Depends(require_admin)):
    try: return get_menu().get("contact", {})
    except (OSError, ValueError) as exc: raise HTTPException(500, str(exc))

@app.put("/api/admin/contact")
def update_contact(body: ContactInput, _email: str = Depends(require_admin)):
    try:
        current = get_menu()
        current["contact"] = body.model_dump()
        save_menu(current)
        return current["contact"]
    except ValueError as exc: raise HTTPException(400, str(exc))

@app.get("/api/admin/users")
def admin_users(_email: str = Depends(require_admin)):
    try: return list_customers()
    except RuntimeError as exc: raise HTTPException(503, str(exc))

@app.post("/api/admin/users", status_code=201)
def add_admin_user(body: CustomerInput, _email: str = Depends(require_admin)):
    try: return create_customer(body.name, body.email, body.phone)
    except ValueError as exc: raise HTTPException(400, str(exc))

@app.put("/api/admin/users/{user_id}")
def edit_admin_user(user_id: int, body: CustomerInput, _email: str = Depends(require_admin)):
    try:
        if not update_customer(user_id, body.name, body.email, body.phone):
            raise HTTPException(404, "Customer record not found")
        return {"id": user_id, **body.model_dump()}
    except ValueError as exc: raise HTTPException(400, str(exc))

@app.delete("/api/admin/users/{user_id}")
def remove_admin_user(user_id: int, _email: str = Depends(require_admin)):
    if not delete_customer(user_id): raise HTTPException(404, "Customer record not found")
    return {"ok": True}

@app.post("/api/orders")
def create_order(body: OrderInput):
    try:
        items, fee = validate_items(body.items)
        return place_order(body.model_dump(), items, fee)
    except ValueError as exc: raise HTTPException(400, str(exc))

@app.get("/api/admin/orders")
def orders(_email: str = Depends(require_admin)): return list_orders()

@app.patch("/api/admin/orders/{order_id}")
def status(order_id: str, body: StatusInput, _email: str = Depends(require_admin)):
    try: result = update_status(order_id, body.status)
    except ValueError as exc: raise HTTPException(400, str(exc))
    if result is None: raise HTTPException(404, "Order not found")
    return result

@app.websocket("/ws/gestures")
async def gestures(websocket: WebSocket):
    await websocket.accept()
    try:
        from .camera import stream_gestures
        async for event in stream_gestures(): await websocket.send_json(event)
    except WebSocketDisconnect: pass
    except Exception as exc:
        try: await websocket.send_json({"type":"error","message":str(exc)})
        except Exception: pass

@app.websocket("/ws/gestures/landmarks")
async def browser_gestures(websocket: WebSocket):
    """Map browser-detected hand landmarks to kiosk controls."""
    import time
    from .gesture_engine import GestureEngine
    await websocket.accept()
    engine = GestureEngine()
    last_landmarks = []
    last_seen = 0.0
    try:
        await websocket.send_json({"type":"status", "camera":"connected",
                                   "trackingAvailable":True})
        while True:
            message = await websocket.receive_json()
            landmarks = message.get("landmarks", [])
            now = time.monotonic()
            if isinstance(landmarks, list) and len(landmarks) >= 21:
                last_landmarks = landmarks
                last_seen = now
            else:
                landmarks = last_landmarks if now - last_seen < 0.18 else []
            gesture = engine.update(landmarks, now)
            await websocket.send_json({"type":"gesture" if gesture else "status",
                                       "gesture":gesture, "camera":"connected",
                                       "detected":engine.detected,
                                       "confidence":engine.confidence,
                                       "tracking":bool(landmarks),
                                       "trackingAvailable":True})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try: await websocket.send_json({"type":"error", "message":str(exc)})
        except Exception: pass

app.mount("/", StaticFiles(directory=ROOT / "frontend", html=True), name="frontend")
