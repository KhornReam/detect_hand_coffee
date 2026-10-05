import sqlite3
import mysql.connector
from mysql.connector import Error
from .config import DB_PATH, MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD

def connect():
    """Open a MySQL connection to the configured application database."""
    try:
        return mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            charset="utf8mb4",
            collation="utf8mb4_0900_ai_ci",
            connection_timeout=5,
            autocommit=False,
        )
    except Error as exc:
        raise RuntimeError(
            f"Cannot connect to MySQL database '{MYSQL_DATABASE}' at {MYSQL_HOST}:{MYSQL_PORT}. "
            "Check that MySQL is running and MYSQL_HOST, MYSQL_PORT, MYSQL_USER, and MYSQL_PASSWORD "
            "in the project .env file are correct."
        ) from exc

def initialize():
    """Create order/customer tables and safely migrate older local orders if present."""
    db = connect()
    try:
        cursor = db.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS orders (
            id VARCHAR(32) NOT NULL PRIMARY KEY,
            idempotency_key VARCHAR(100) NOT NULL UNIQUE,
            created_at VARCHAR(40) NOT NULL,
            status VARCHAR(20) NOT NULL,
            total DECIMAL(10, 2) NOT NULL,
            payload JSON NOT NULL,
            INDEX idx_orders_created_at (created_at),
            INDEX idx_orders_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS customer_records (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(120) NOT NULL,
            email VARCHAR(254) NOT NULL,
            phone VARCHAR(40) NOT NULL DEFAULT '',
            created_at VARCHAR(40) NOT NULL,
            UNIQUE KEY uq_customer_records_email (email),
            INDEX idx_customer_records_name (name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS customer_accounts (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(120) NOT NULL,
            email VARCHAR(254) NOT NULL UNIQUE,
            password_hash VARCHAR(160) NOT NULL,
            created_at VARCHAR(40) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS contact_messages (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(120) NOT NULL,
            email VARCHAR(254) NOT NULL,
            subject VARCHAR(160) NOT NULL DEFAULT '',
            message TEXT NOT NULL,
            created_at VARCHAR(40) NOT NULL,
            INDEX idx_contact_messages_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci""")
        db.commit()
        _migrate_sqlite_orders(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def _migrate_sqlite_orders(mysql_db):
    """Idempotently import existing MVP orders; never modify or remove the SQLite file."""
    if not DB_PATH.exists():
        return
    sqlite_db = sqlite3.connect(DB_PATH)
    sqlite_db.row_factory = sqlite3.Row
    try:
        table = sqlite_db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='orders'"
        ).fetchone()
        if not table:
            return
        rows = sqlite_db.execute(
            "SELECT id, idempotency_key, created_at, status, total, payload FROM orders"
        ).fetchall()
        if not rows:
            return
        cursor = mysql_db.cursor()
        cursor.executemany(
            """INSERT IGNORE INTO orders
               (id, idempotency_key, created_at, status, total, payload)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            [(r["id"], r["idempotency_key"], r["created_at"], r["status"],
              r["total"], r["payload"]) for r in rows],
        )
        mysql_db.commit()
    finally:
        sqlite_db.close()

def database_health():
    db = connect()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT DATABASE(), VERSION()")
        database, version = cursor.fetchone()
        return {"database": database, "mysqlVersion": version, "connection": "connected"}
    finally:
        db.close()
