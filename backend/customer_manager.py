"""Admin-managed customer contact records (not login accounts)."""
import re
from datetime import datetime, timezone

from mysql.connector import IntegrityError

from .database import connect


def _clean(name, email, phone):
    name = str(name or "").strip()
    email = str(email or "").strip().casefold()
    phone = str(phone or "").strip()
    if not name or len(name) > 120:
        raise ValueError("Customer name must be between 1 and 120 characters")
    if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValueError("Enter a valid customer email address")
    if len(phone) > 40:
        raise ValueError("Phone number is too long")
    return name, email, phone


def list_customers():
    db = connect()
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id, name, email, phone, created_at AS createdAt FROM customer_records ORDER BY id DESC")
        return cursor.fetchall()
    finally:
        db.close()


def create_customer(name, email, phone=""):
    name, email, phone = _clean(name, email, phone)
    created_at = datetime.now(timezone.utc).isoformat()
    db = connect()
    try:
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO customer_records (name,email,phone,created_at) VALUES (%s,%s,%s,%s)",
                           (name, email, phone, created_at))
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("A customer with that email already exists") from exc
        return {"id": cursor.lastrowid, "name": name, "email": email, "phone": phone, "createdAt": created_at}
    finally:
        db.close()


def update_customer(customer_id, name, email, phone=""):
    name, email, phone = _clean(name, email, phone)
    db = connect()
    try:
        cursor = db.cursor()
        try:
            cursor.execute("UPDATE customer_records SET name=%s,email=%s,phone=%s WHERE id=%s",
                           (name, email, phone, customer_id))
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("A customer with that email already exists") from exc
        return cursor.rowcount > 0
    finally:
        db.close()


def delete_customer(customer_id):
    db = connect()
    try:
        cursor = db.cursor()
        cursor.execute("DELETE FROM customer_records WHERE id=%s", (customer_id,))
        db.commit()
        return cursor.rowcount > 0
    finally:
        db.close()
