import pytest
import sqlite3
import sys
import os
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.db import init_db
from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def seed_db():
    init_db()
    conn = sqlite3.connect("spendly.db")
    conn.execute("DELETE FROM expenses")
    conn.execute("DELETE FROM users")
    conn.commit()
    password_hash = generate_password_hash("demo123")
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        ("Test User", "test@test.com", password_hash, "2026-01-15 10:00:00")
    )
    user_id = cur.lastrowid
    expenses = [
        (user_id, 100.0, "Food", "2026-01-10", "Groceries"),
        (user_id, 50.0, "Transport", "2026-01-12", "Uber"),
        (user_id, 75.0, "Food", "2026-01-14", "Lunch"),
        (user_id, 200.0, "Bills", "2026-01-08", "Electricity"),
    ]
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        expenses
    )
    conn.commit()
    conn.close()
    return user_id


class TestGetUserById:
    def test_returns_correct_user_data(self, seed_db):
        user = get_user_by_id(seed_db)
        assert user is not None
        assert user["name"] == "Test User"
        assert user["email"] == "test@test.com"
        assert "member_since" in user

    def test_returns_none_for_nonexistent_user(self):
        user = get_user_by_id(99999)
        assert user is None


class TestGetSummaryStats:
    def test_returns_correct_totals(self, seed_db):
        stats = get_summary_stats(seed_db)
        assert stats["total_spent"] == 425.0
        assert stats["transaction_count"] == 4

    def test_top_category_is_bills(self, seed_db):
        stats = get_summary_stats(seed_db)
        assert stats["top_category"] == "Bills"

    def test_no_expenses_returns_zeros(self):
        conn = sqlite3.connect("spendly.db")
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            ("Empty User", "empty@test.com", generate_password_hash("demo123"), "2026-01-01")
        )
        empty_user_id = cur.lastrowid
        conn.commit()
        conn.close()

        stats = get_summary_stats(empty_user_id)
        assert stats["total_spent"] == 0.0
        assert stats["transaction_count"] == 0
        assert stats["top_category"] == "—"


class TestGetRecentTransactions:
    def test_returns_transactions_newest_first(self, seed_db):
        txs = get_recent_transactions(seed_db)
        assert len(txs) == 4
        assert txs[0]["date"] == "2026-01-14"
        assert txs[1]["date"] == "2026-01-12"

    def test_each_transaction_has_required_keys(self, seed_db):
        txs = get_recent_transactions(seed_db)
        for tx in txs:
            assert "date" in tx
            assert "description" in tx
            assert "category" in tx
            assert "amount" in tx

    def test_no_transactions_returns_empty_list(self):
        conn = sqlite3.connect("spendly.db")
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            ("No Tx User", "notx@test.com", generate_password_hash("demo123"), "2026-01-01")
        )
        no_tx_user_id = cur.lastrowid
        conn.commit()
        conn.close()

        txs = get_recent_transactions(no_tx_user_id)
        assert txs == []


class TestGetCategoryBreakdown:
    def test_categories_ordered_by_amount_desc(self, seed_db):
        breakdown = get_category_breakdown(seed_db)
        amounts = [cat["amount"] for cat in breakdown]
        assert amounts == sorted(amounts, reverse=True)

    def test_percentages_sum_to_100(self, seed_db):
        breakdown = get_category_breakdown(seed_db)
        total_pct = sum(cat["pct"] for cat in breakdown)
        assert total_pct == 100

    def test_each_category_has_required_keys(self, seed_db):
        breakdown = get_category_breakdown(seed_db)
        for cat in breakdown:
            assert "name" in cat
            assert "amount" in cat
            assert "pct" in cat

    def test_no_expenses_returns_empty_list(self):
        conn = sqlite3.connect("spendly.db")
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            ("No Cat User", "nocat@test.com", generate_password_hash("demo123"), "2026-01-01")
        )
        no_cat_user_id = cur.lastrowid
        conn.commit()
        conn.close()

        breakdown = get_category_breakdown(no_cat_user_id)
        assert breakdown == []


class TestProfileRoute:
    def test_unauthenticated_redirects_to_login(self, client):
        response = client.get("/profile", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.location

    def test_authenticated_returns_200_with_user_data(self, client, seed_db):
        # Login first
        client.post("/login", data={
            "email": "test@test.com",
            "password": "demo123"
        }, follow_redirects=True)

        response = client.get("/profile")
        assert response.status_code == 200
        data = response.get_data(as_text=True)
        assert "Test User" in data
        assert "test@test.com" in data
        assert "₹" in data

    def test_authenticated_shows_correct_totals(self, client, seed_db):
        client.post("/login", data={
            "email": "test@test.com",
            "password": "demo123"
        }, follow_redirects=True)

        response = client.get("/profile")
        data = response.get_data(as_text=True)
        # 100 + 50 + 75 + 200 = 425
        assert "425.00" in data
        assert "4" in data  # transaction count
        assert "Bills" in data  # top category

    def test_authenticated_shows_transaction_table(self, client, seed_db):
        client.post("/login", data={
            "email": "test@test.com",
            "password": "demo123"
        }, follow_redirects=True)

        response = client.get("/profile")
        data = response.get_data(as_text=True)
        assert "Groceries" in data
        assert "Uber" in data
        assert "Lunch" in data

    def test_authenticated_shows_category_breakdown(self, client, seed_db):
        client.post("/login", data={
            "email": "test@test.com",
            "password": "demo123"
        }, follow_redirects=True)

        response = client.get("/profile")
        data = response.get_data(as_text=True)
        assert "Food" in data
        assert "Transport" in data
        assert "Bills" in data