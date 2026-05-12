import sqlite3
from datetime import date
from werkzeug.security import generate_password_hash


def create_user(name, email, password):
    """Hash password and insert a new user. Raises sqlite3.IntegrityError if email exists."""
    conn = get_db()
    try:
        password_hash = generate_password_hash(password)
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_user_by_email(email):
    """Fetch a user by email. Returns a row dict or None."""
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT id, name, email, password_hash, created_at FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        return user
    finally:
        conn.close()


def get_db():
    """Returns a SQLite connection with row_factory and foreign keys enabled."""
    conn = sqlite3.connect("spendly.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Creates users and expenses tables using CREATE TABLE IF NOT EXISTS."""
    conn = get_db()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                date TEXT NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.commit()
    finally:
        conn.close()


def seed_db():
    """Inserts demo user and 8 sample expenses if users table is empty."""
    conn = get_db()
    try:
        existing = conn.execute("SELECT COUNT(*) as count FROM users").fetchone()
        if existing["count"] > 0:
            return

        password_hash = generate_password_hash("demo123")
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", password_hash)
        )
        user_id = cur.lastrowid

        today = date.today()
        expenses = [
            (user_id, 15.50, "Food", str(today.replace(day=1)), "Coffee and breakfast"),
            (user_id, 45.00, "Transport", str(today.replace(day=2)), "Uber to work"),
            (user_id, 120.00, "Bills", str(today.replace(day=3)), "Electricity bill"),
            (user_id, 30.00, "Health", str(today.replace(day=4)), "Pharmacy"),
            (user_id, 25.00, "Entertainment", str(today.replace(day=5)), "Movie tickets"),
            (user_id, 80.00, "Shopping", str(today.replace(day=6)), "New shoes"),
            (user_id, 20.00, "Food", str(today.replace(day=7)), "Lunch with colleague"),
            (user_id, 12.50, "Other", str(today.replace(day=8)), "Misc purchase"),
        ]

        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            expenses
        )
        conn.commit()
    finally:
        conn.close()