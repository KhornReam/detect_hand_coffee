import json
import secrets
from datetime import datetime, timezone
from mysql.connector import IntegrityError
from .database import connect

def _decode_order(value):
    return json.loads(value) if isinstance(value, (str, bytes, bytearray)) else value

def place_order(payload, items, service_fee=0):
    key = payload.get("idempotencyKey")
    if not key or len(str(key)) > 100 or not isinstance(items, list) or not items:
        raise ValueError("A non-empty order and idempotency key are required")
    if len(items) > 30:
        raise ValueError("Too many line items")
    for item in items:
        if type(item.get("quantity")) is not int or not 1 <= item["quantity"] <= 20:
            raise ValueError("Quantity must be between 1 and 20")
        if not isinstance(item.get("unitPrice"), (int, float)) or item["unitPrice"] < 0:
            raise ValueError("Invalid item price")
    total = round(sum(item["unitPrice"] * item["quantity"] for item in items) + service_fee, 2)
    now = datetime.now(timezone.utc).isoformat()
    order_id = "BRC-" + datetime.now().strftime("%y%m%d") + "-" + secrets.token_hex(4).upper()
    order = {"id": order_id, "createdAt": now, "status": "PENDING", "total": total, "items": items}
    db = connect()
    try:
        cursor = db.cursor(dictionary=True)
        db.start_transaction()
        cursor.execute("SELECT payload FROM orders WHERE idempotency_key=%s", (key,))
        prior = cursor.fetchone()
        if prior:
            db.commit()
            return _decode_order(prior["payload"])
        try:
            cursor.execute(
                """INSERT INTO orders (id,idempotency_key,created_at,status,total,payload)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (order_id, key, now, "PENDING", total, json.dumps(order, separators=(",", ":"))),
            )
            db.commit()
            return order
        except IntegrityError:
            db.rollback()
            cursor.execute("SELECT payload FROM orders WHERE idempotency_key=%s", (key,))
            prior = cursor.fetchone()
            if prior:
                return _decode_order(prior["payload"])
            raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def list_orders():
    db = connect()
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT payload FROM orders ORDER BY created_at DESC")
        return [_decode_order(row["payload"]) for row in cursor.fetchall()]
    finally:
        db.close()

def update_status(order_id, status):
    allowed = {"PENDING", "PREPARING", "READY", "COMPLETED"}
    if status not in allowed:
        raise ValueError("Unknown order status")
    db = connect()
    try:
        cursor = db.cursor(dictionary=True)
        db.start_transaction()
        cursor.execute("SELECT payload FROM orders WHERE id=%s FOR UPDATE", (order_id,))
        row = cursor.fetchone()
        if not row:
            db.commit()
            return None
        order = _decode_order(row["payload"])
        order["status"] = status
        cursor.execute("UPDATE orders SET status=%s, payload=%s WHERE id=%s",
                       (status, json.dumps(order, separators=(",", ":")), order_id))
        db.commit()
        return order
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
