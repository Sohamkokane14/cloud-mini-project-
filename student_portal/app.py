"""Student-facing Lost & Found portal hosted on Azure App Service."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, send_from_directory, url_for

from shared import db, matching, storage, vision


CATEGORIES = ("Electronics", "ID Card", "Books", "Bottle", "Bag", "Keys", "Clothing", "Other")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}


def _current_user() -> str:
    """Read App Service authentication identity, with a safe mock-mode fallback."""
    return request.headers.get("X-MS-CLIENT-PRINCIPAL-NAME", "demo@student.local")


def _valid_upload(filename: str) -> bool:
    """Accept only the image formats specified in the project scope."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def create_app() -> Flask:
    """Create the Student Portal Flask application."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "mock-mode-session-key")
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
    db.init_db()

    @app.context_processor
    def template_context() -> dict:
        return {"categories": CATEGORIES, "today": date.today().isoformat()}

    @app.get("/health")
    def health():
        """Provide a small health probe for App Service."""
        return jsonify({"status": "ok"})

    @app.get("/")
    def home():
        """Show dashboard counts and recent reports."""
        return render_template("home.html", stats=db.get_stats(), items=db.list_items(limit=6))

    @app.route("/report/<item_type>", methods=["GET", "POST"])
    def report(item_type: str):
        """Create a lost or found report and display any suggested matches."""
        if item_type not in {"lost", "found"}:
            abort(404)
        if request.method == "GET":
            return render_template("report.html", item_type=item_type)
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        if not title or category not in CATEGORIES:
            flash("Please enter a title and select a category.", "danger")
            return render_template("report.html", item_type=item_type), 400
        photo = request.files.get("photo")
        image_url, analysis = "", {"tags": [], "caption": ""}
        if photo and photo.filename:
            if not _valid_upload(photo.filename):
                flash("Upload a JPG or PNG image only.", "danger")
                return render_template("report.html", item_type=item_type), 400
            image_bytes = photo.read()
            if not image_bytes:
                flash("The uploaded image is empty.", "danger")
                return render_template("report.html", item_type=item_type), 400
            analysis = vision.analyze_image(image_bytes, category)
            photo.stream.seek(0)
            image_url = storage.upload_image(photo)
        item_id = db.create_item({
            "Type": item_type,
            "Title": title,
            "Description": request.form.get("description", "").strip(),
            "Category": category,
            "Location": request.form.get("location", "").strip(),
            "ItemDate": request.form.get("item_date") or None,
            "ImageUrl": image_url,
            "Tags": analysis["tags"],
            "Caption": analysis["caption"],
            "ReporterName": _current_user().split("@", 1)[0],
            "ReporterEmail": _current_user(),
        })
        suggestions = matching.find_and_store_matches(item_id)
        flash("Your report was submitted successfully.", "success")
        return render_template("item_detail.html", item=db.get_item(item_id), matches=suggestions, submitted=True)

    @app.get("/browse")
    def browse():
        """Browse reports with type, category, and text filters."""
        item_type = request.args.get("type") or None
        category = request.args.get("category") or None
        keyword = request.args.get("q", "").strip() or None
        if item_type not in {None, "lost", "found"}:
            item_type = None
        if category not in set(CATEGORIES):
            category = None
        return render_template(
            "browse.html", items=db.list_items(type=item_type, category=category, keyword=keyword),
            selected_type=item_type, selected_category=category, keyword=keyword or "",
        )

    @app.get("/my-items")
    def my_items():
        """Show the current student's own reports and their suggestions."""
        items = db.list_items(reporter_email=_current_user(), limit=100)
        matches = {item["ItemId"]: db.list_matches(item["ItemId"]) for item in items}
        return render_template("my_items.html", items=items, matches=matches)

    @app.get("/items/<int:item_id>")
    def item_detail(item_id: int):
        """Show one item and all of its known match suggestions."""
        item = db.get_item(item_id)
        if not item:
            abort(404)
        return render_template("item_detail.html", item=item, matches=db.list_matches(item_id))

    @app.get("/local_uploads/<path:filename>")
    def local_upload(filename: str):
        """Serve mock-mode images locally; cloud images are served by Blob Storage."""
        directory = Path(__file__).resolve().parents[1] / "local_uploads"
        return send_from_directory(directory, filename)

    @app.errorhandler(413)
    def too_large(_error):
        return render_template("error.html", message="Images must be 5 MB or smaller."), 413

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", message="That item could not be found."), 404

    @app.errorhandler(RuntimeError)
    def service_unavailable(_error):
        return render_template(
            "error.html", message="The data service may be waking up. Please wait a minute and try again."
        ), 503

    return app


app = create_app()
