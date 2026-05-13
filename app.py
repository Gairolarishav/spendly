from flask import Flask, render_template, flash, redirect, request, abort, session, g, url_for
from werkzeug.security import check_password_hash
import sqlite3
from database.db import get_db, init_db, seed_db, create_user, get_user_by_email

app = Flask(__name__)
app.secret_key = "dev-secret-key"


@app.context_processor
def inject_user_name():
    user_name = None
    if "user_id" in session:
        conn = get_db()
        row = conn.execute("SELECT name FROM users WHERE id = ?", (session["user_id"],)).fetchone()
        if row:
            user_name = row["name"]
        conn.close()
    return dict(user_name=user_name)


@app.before_request
def load_user():
    g.user_name = None
    if "user_id" in session:
        conn = get_db()
        row = conn.execute("SELECT name FROM users WHERE id = ?", (session["user_id"],)).fetchone()
        if row:
            g.user_name = row["name"]
        conn.close()

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect("/")

    if request.method == "GET":
        return render_template("register.html")

    if request.method != "POST":
        abort(405)

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not name or not email or not password or not confirm_password:
        flash("Please fill in all fields.", "error")
        return render_template("register.html", name=name, email=email)

    if password != confirm_password:
        flash("Passwords do not match.", "error")
        return render_template("register.html", name=name, email=email)

    try:
        create_user(name, email, password)
        flash("Account created! Please sign in.", "success")
        return redirect("/login")
    except sqlite3.IntegrityError:
        flash("Email already registered.", "error")
        return render_template("register.html", name=name, email=email)


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect("/")

    if request.method == "GET":
        return render_template("login.html")

    if request.method != "POST":
        abort(405)

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not email or not password:
        flash("Please enter your email and password.", "error")
        return render_template("login.html", email=email)

    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        flash("Invalid email or password.", "error")
        return render_template("login.html", email=email)

    session["user_id"] = user["id"]
    session["user_email"] = user["email"]
    flash("Welcome back!", "success")
    return redirect("/profile")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect("/")


@app.route("/profile")
def profile():
    """Profile page - displays user info, stats, transactions, and category breakdown."""
    if not session.get("user_id"):
        return redirect(url_for("login"))

    # Hardcoded user data (no DB query in this step)
    user = {
        "name": "Demo User",
        "email": "demo@spendly.com",
        "member_since": "January 2025",
        "initials": "DU"
    }

    # Hardcoded summary stats
    stats = {
        "total_spent": 1234.50,
        "transaction_count": 8,
        "top_category": "Food"
    }

    # Hardcoded transaction history (at least 3 rows as per spec)
    transactions = [
        {"date": "2025-05-08", "description": "Misc purchase", "category": "Other", "amount": 12.50},
        {"date": "2025-05-07", "description": "New shoes", "category": "Shopping", "amount": 80.00},
        {"date": "2025-05-05", "description": "Movie tickets", "category": "Entertainment", "amount": 25.00},
        {"date": "2025-05-04", "description": "Pharmacy", "category": "Health", "amount": 30.00},
        {"date": "2025-05-03", "description": "Electricity bill", "category": "Bills", "amount": 120.00},
    ]

    # Hardcoded category breakdown (at least 3 categories as per spec)
    categories = [
        {"name": "Food", "amount": 45.50, "percentage": 37},
        {"name": "Transport", "amount": 45.00, "percentage": 36},
        {"name": "Bills", "amount": 120.00, "percentage": 100},
        {"name": "Shopping", "amount": 80.00, "percentage": 65},
    ]

    return render_template("profile.html", user=user, stats=stats, transactions=transactions, categories=categories)


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
