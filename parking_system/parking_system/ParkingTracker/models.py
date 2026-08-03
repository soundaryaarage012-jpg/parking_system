import hashlib
import sqlite3
from datetime import datetime
from functools import wraps
from typing import Optional

from flask import g, session

from config import DB_PATH


def get_db():
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.commit()
        db.close()


def _column_exists(conn, table_name, column_name):
    columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(column[1] == column_name for column in columns)


def _add_column(conn, table_name, column_name, definition):
    if not _column_exists(conn, table_name, column_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            phone TEXT,
            vehicle_number TEXT,
            vehicle_type TEXT DEFAULT 'Sedan',
            role TEXT DEFAULT 'user',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS parking_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slot_number TEXT UNIQUE NOT NULL,
            block_name TEXT NOT NULL,
            floor TEXT DEFAULT 'Ground Floor',
            status TEXT DEFAULT 'available',
            reserved_by INTEGER,
            occupied_by INTEGER,
            distance_from_entrance INTEGER DEFAULT 60,
            ev_charging INTEGER DEFAULT 0,
            priority INTEGER DEFAULT 1,
            vehicle_size TEXT DEFAULT 'Sedan'
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS parking_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            slot_id INTEGER NOT NULL,
            entry_time TEXT NOT NULL,
            exit_time TEXT,
            duration TEXT,
            vehicle_number TEXT,
            reservation_time TEXT,
            plate_image TEXT,
            ocr_text TEXT,
            confidence_score REAL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            slot_id INTEGER NOT NULL,
            reservation_time TEXT NOT NULL,
            expiry_time TEXT NOT NULL,
            status TEXT DEFAULT 'active'
        )
        """
    )
    conn.commit()

    _add_column(conn, "users", "vehicle_type", "TEXT DEFAULT 'Sedan'")
    _add_column(conn, "parking_slots", "floor", "TEXT DEFAULT 'Ground Floor'")
    _add_column(conn, "parking_slots", "distance_from_entrance", "INTEGER DEFAULT 60")
    _add_column(conn, "parking_slots", "ev_charging", "INTEGER DEFAULT 0")
    _add_column(conn, "parking_slots", "priority", "INTEGER DEFAULT 1")
    _add_column(conn, "parking_slots", "vehicle_size", "TEXT DEFAULT 'Sedan'")
    _add_column(conn, "parking_history", "vehicle_number", "TEXT")
    _add_column(conn, "parking_history", "reservation_time", "TEXT")
    _add_column(conn, "parking_history", "plate_image", "TEXT")
    _add_column(conn, "parking_history", "ocr_text", "TEXT")
    _add_column(conn, "parking_history", "confidence_score", "REAL")
    conn.commit()

    admin_exists = conn.execute("SELECT id, password FROM users WHERE email = ?", ("admin@example.com",)).fetchone()
    if not admin_exists:
        conn.execute(
            "INSERT INTO users (full_name, email, password, phone, vehicle_number, vehicle_type, role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("Administrator", "admin@example.com", hash_password("admin123"), "0000000000", "NA", "Sedan", "admin", datetime.now().isoformat()),
        )
    else:
        stored_hash = admin_exists[1]
        if stored_hash == "admin123" or stored_hash == hash_password("admin123"):
            conn.execute(
                "UPDATE users SET password = ? WHERE email = ?",
                (hash_password("admin123"), "admin@example.com"),
            )
    slot_count = conn.execute("SELECT COUNT(*) FROM parking_slots").fetchone()[0]
    if slot_count == 0:
        sample_slots = [
            ("P10", "Ground Floor", "Ground Floor", "available", None, None, 40, 1, 2, "Sedan"),
            ("P11", "Ground Floor", "Ground Floor", "available", None, None, 55, 0, 1, "Sedan"),
            ("P12", "Ground Floor", "Ground Floor", "reserved", None, None, 65, 0, 2, "SUV"),
            ("P20", "First Floor", "First Floor", "occupied", None, None, 90, 1, 3, "Sedan"),
            ("P21", "First Floor", "First Floor", "available", None, None, 110, 0, 1, "SUV"),
            ("P30", "Second Floor", "Second Floor", "available", None, None, 130, 1, 2, "Sedan"),
        ]
        conn.executemany(
            "INSERT INTO parking_slots (slot_number, block_name, floor, status, reserved_by, occupied_by, distance_from_entrance, ev_charging, priority, vehicle_size) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            sample_slots,
        )
    elif slot_count < 12:
        existing_numbers = {row[0] for row in conn.execute("SELECT slot_number FROM parking_slots").fetchall()}
        more_slots = [
            ("B02", "First Floor", "First Floor", "available", None, None, 95, 0, 1, "Sedan"),
            ("B03", "First Floor", "First Floor", "available", None, None, 100, 1, 2, "SUV"),
            ("C01", "Second Floor", "Second Floor", "occupied", None, None, 145, 0, 2, "Sedan"),
            ("C02", "Second Floor", "Second Floor", "available", None, None, 150, 1, 3, "SUV"),
            ("C03", "Second Floor", "Second Floor", "available", None, None, 160, 0, 1, "Sedan"),
            ("D01", "Third Floor", "Third Floor", "available", None, None, 180, 1, 2, "Sedan"),
        ]
        conn.executemany(
            "INSERT OR IGNORE INTO parking_slots (slot_number, block_name, floor, status, reserved_by, occupied_by, distance_from_entrance, ev_charging, priority, vehicle_size) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [slot for slot in more_slots if slot[0] not in existing_numbers],
        )
    conn.commit()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def check_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed


def get_current_user() -> Optional[sqlite3.Row]:
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def get_dashboard_stats():
    conn = get_db()
    total_slots = conn.execute("SELECT COUNT(*) FROM parking_slots").fetchone()[0]
    available_slots = conn.execute("SELECT COUNT(*) FROM parking_slots WHERE status = 'available'").fetchone()[0]
    occupied_slots = conn.execute("SELECT COUNT(*) FROM parking_slots WHERE status = 'occupied'").fetchone()[0]
    reserved_slots = conn.execute("SELECT COUNT(*) FROM parking_slots WHERE status = 'reserved'").fetchone()[0]
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    today = datetime.now().strftime("%Y-%m-%d")
    todays_entries = conn.execute("SELECT COUNT(*) FROM parking_history WHERE entry_time LIKE ?", (f"{today}%",)).fetchone()[0]
    todays_exits = conn.execute("SELECT COUNT(*) FROM parking_history WHERE exit_time LIKE ?", (f"{today}%",)).fetchone()[0]
    recent_activity = conn.execute(
        "SELECT ph.id, u.full_name, s.slot_number, ph.entry_time, ph.exit_time, ph.duration FROM parking_history ph JOIN users u ON u.id = ph.user_id JOIN parking_slots s ON s.id = ph.slot_id ORDER BY ph.id DESC LIMIT 8"
    ).fetchall()
    return {
        "total_slots": total_slots,
        "available_slots": available_slots,
        "occupied_slots": occupied_slots,
        "reserved_slots": reserved_slots,
        "total_users": total_users,
        "todays_entries": todays_entries,
        "todays_exits": todays_exits,
        "recent_activity": recent_activity,
    }


def get_parking_slots(filters=None):
    conn = get_db()
    query = "SELECT * FROM parking_slots"
    params = []
    conditions = []
    if filters:
        if filters.get("status"):
            conditions.append("status = ?")
            params.append(filters["status"])
        if filters.get("block_name"):
            conditions.append("block_name = ?")
            params.append(filters["block_name"])
        if filters.get("floor"):
            conditions.append("floor = ?")
            params.append(filters["floor"])
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY slot_number"
    return conn.execute(query, params).fetchall()


def search_slots(term):
    conn = get_db()
    term = f"%{term}%"
    return conn.execute(
        "SELECT * FROM parking_slots WHERE slot_number LIKE ? OR block_name LIKE ? OR floor LIKE ?",
        (term, term, term),
    ).fetchall()


def search_users(term):
    conn = get_db()
    term = f"%{term}%"
    return conn.execute(
        "SELECT * FROM users WHERE full_name LIKE ? OR email LIKE ? OR vehicle_number LIKE ?",
        (term, term, term),
    ).fetchall()


def get_history(user_id=None, search=None):
    conn = get_db()
    query = "SELECT ph.*, u.full_name, u.vehicle_number, s.slot_number FROM parking_history ph JOIN users u ON u.id = ph.user_id JOIN parking_slots s ON s.id = ph.slot_id"
    params = []
    if user_id:
        query += " WHERE ph.user_id = ?"
        params.append(user_id)
    if search:
        if user_id:
            query += " AND (u.full_name LIKE ? OR u.vehicle_number LIKE ? OR s.slot_number LIKE ?)"
        else:
            query += " WHERE (u.full_name LIKE ? OR u.vehicle_number LIKE ? OR s.slot_number LIKE ?)"
        search_term = f"%{search}%"
        params.extend([search_term, search_term, search_term])
    query += " ORDER BY ph.id DESC"
    return conn.execute(query, params).fetchall()


def get_reservations(user_id=None):
    conn = get_db()
    if user_id:
        return conn.execute(
            "SELECT r.*, s.slot_number, s.block_name FROM reservations r JOIN parking_slots s ON s.id = r.slot_id WHERE r.user_id = ? AND r.status = 'active' ORDER BY r.id DESC",
            (user_id,),
        ).fetchall()
    return conn.execute(
        "SELECT r.*, s.slot_number, s.block_name FROM reservations r JOIN parking_slots s ON s.id = r.slot_id ORDER BY r.id DESC"
    ).fetchall()


def create_reservation(user_id, slot_id, expiry_time):
    conn = get_db()
    conn.execute(
        "INSERT INTO reservations (user_id, slot_id, reservation_time, expiry_time, status) VALUES (?, ?, ?, ?, 'active')",
        (user_id, slot_id, datetime.now().isoformat(), expiry_time),
    )
    conn.commit()


def update_slot_status(slot_id, status, user_id=None):
    conn = get_db()
    if status == "available":
        conn.execute(
            "UPDATE parking_slots SET status = ?, reserved_by = NULL, occupied_by = NULL WHERE id = ?",
            (status, slot_id),
        )
    elif status == "reserved":
        conn.execute(
            "UPDATE parking_slots SET status = ?, reserved_by = ?, occupied_by = NULL WHERE id = ?",
            (status, user_id, slot_id),
        )
    elif status == "occupied":
        conn.execute(
            "UPDATE parking_slots SET status = ?, reserved_by = NULL, occupied_by = ? WHERE id = ?",
            (status, user_id, slot_id),
        )
    conn.commit()


def log_history(user_id, slot_id, entry_time, exit_time=None, duration=None, vehicle_number=None, reservation_time=None, plate_image=None, ocr_text=None, confidence_score=None):
    conn = get_db()
    conn.execute(
        "INSERT INTO parking_history (user_id, slot_id, entry_time, exit_time, duration, vehicle_number, reservation_time, plate_image, ocr_text, confidence_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, slot_id, entry_time, exit_time, duration, vehicle_number, reservation_time, plate_image, ocr_text, confidence_score),
    )
    conn.commit()
