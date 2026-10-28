"""Gunicorn entry point for the VM-hosted Admin Panel."""

from admin_panel.app import app


if __name__ == "__main__":
    app.run()
