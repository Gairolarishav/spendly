from database.db import get_db


def get_user_by_id(user_id):
    """Return user info dict with name, email, member_since (formatted from created_at)."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        if not row:
            return None
        member_since = row["created_at"].strftime("%B %Y") if hasattr(row["created_at"], "strftime") else row["created_at"][:7]
        return {
            "name": row["name"],
            "email": row["email"],
            "created_at": row["created_at"],
            "member_since": member_since
        }
    finally:
        conn.close()


def get_summary_stats(user_id):
    """Return dict with total_spent, transaction_count, top_category."""
    conn = get_db()
    try:
        stats = conn.execute(
            "SELECT SUM(amount) as total, COUNT(*) as count FROM expenses WHERE user_id = ?",
            (user_id,)
        ).fetchone()

        if not stats or stats["count"] == 0:
            return {"total_spent": 0.0, "transaction_count": 0, "top_category": "—"}

        top_row = conn.execute(
            "SELECT category FROM expenses WHERE user_id = ? GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            (user_id,)
        ).fetchone()
        top_category = top_row["category"] if top_row else "—"

        return {
            "total_spent": stats["total"] or 0.0,
            "transaction_count": stats["count"],
            "top_category": top_category
        }
    finally:
        conn.close()


def get_recent_transactions(user_id, limit=10):
    """Return the most recent transactions for a user as a list of dicts."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT date, description, category, amount FROM expenses WHERE user_id = ? ORDER BY date DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_category_breakdown(user_id):
    """Return per-category spending totals with percentages."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category, SUM(amount) as total FROM expenses WHERE user_id = ? GROUP BY category ORDER BY total DESC",
            (user_id,)
        ).fetchall()

        if not rows:
            return []

        total_spent = sum(row["total"] for row in rows)

        breakdown = []
        for row in rows:
            pct = round((row["total"] / total_spent) * 100)
            breakdown.append({
                "name": row["category"],
                "amount": row["total"],
                "pct": pct
            })

        # Adjust largest category to absorb rounding remainder so percentages sum to 100
        total_pct = sum(item["pct"] for item in breakdown)
        remainder = 100 - total_pct
        if remainder != 0 and breakdown:
            breakdown[0]["pct"] += remainder

        return breakdown
    finally:
        conn.close()