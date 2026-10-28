"""Staff-facing administration portal deployed to the Azure VM."""

from __future__ import annotations

import os
import socket
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from shared import db, storage
from shared.config import APP_MODE, get_secret


def _password_hash() -> str:
    """Read the Key Vault/local hash, with a non-production mock fallback."""
    if APP_MODE == "mock":
        return os.getenv("MOCK_ADMIN_PASSWORD_HASH", generate_password_hash("admin"))
    return get_secret("AdminPasswordHash")


def login_required(view):
    """Require a successful admin session for protected views."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Please sign in to access the Admin Panel.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def create_app() -> Flask:
    """Create the Admin Panel Flask application."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "mock-mode-admin-session-key")
    db.init_db()

    @app.context_processor
    def template_context() -> dict:
        return {"hostname": socket.gethostname()}

    @app.route("/login", methods=["GET", "POST"])
    def login():
        """Authenticate the fixed admin account with a hashed password."""
        if request.method == "POST":
            if request.form.get("username") == "admin" and check_password_hash(
                _password_hash(), request.form.get("password", "")
            ):
                session.clear()
                session["is_admin"] = True
                return redirect(url_for("dashboard"))
            flash("Invalid username or password.", "danger")
        return render_template("login.html")

    @app.post("/logout")
    def logout():
        """End the current admin session."""
        session.clear()
        flash("You have been signed out.", "success")
        return redirect(url_for("login"))

    @app.get("/")
    @login_required
    def dashboard():
        """Show item counts, category-chart data, and recent activity."""
        stats = db.get_stats()
        return render_template("dashboard.html", stats=stats, recent=db.list_items(limit=8))

    @app.get("/items")
    @login_required
    def items():
        """List every item for staff review."""
        return render_template("items.html", items=db.list_items(limit=200))

    @app.post("/items/<int:item_id>/returned")
    @login_required
    def mark_returned(item_id: int):
        """Mark an item returned after staff handoff."""
        db.update_item_status(item_id, "returned")
        flash("Item marked as returned.", "success")
        return redirect(url_for("items"))

    @app.post("/items/<int:item_id>/delete")
    @login_required
    def delete_item(item_id: int):
        """Delete an item and its linked image where applicable."""
        image_url = db.delete_item(item_id)
        if image_url is None:
            flash("Item was not found.", "warning")
        else:
            storage.delete_image(image_url)
            flash("Item and linked matches were deleted.", "success")
        return redirect(url_for("items"))

    @app.get("/matches")
    @login_required
    def matches():
        """Show staff-reviewable matching suggestions."""
        return render_template("matches.html", matches=db.list_matches())

    @app.post("/matches/<int:match_id>/<decision>")
    @login_required
    def decide_match(match_id: int, decision: str):
        """Confirm or reject a suggested match."""
        if decision not in {"confirmed", "rejected"}:
            return render_template("error.html", message="Unknown match decision."), 400
        db.update_match_status(match_id, decision)
        flash(f"Match {decision}.", "success")
        return redirect(url_for("matches"))

    return app


app = create_app()
