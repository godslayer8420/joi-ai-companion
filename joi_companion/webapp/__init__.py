"""joi_companion.webapp — Flask application factory and blueprint registry.

Incrementally extracted from the monolithic web_ui.py (61k lines).
New routes go into blueprints/ sub-modules; legacy routes remain in web_ui.py
until each domain is fully extracted.

Blueprint domains (extraction status):
  avatar       — EXTRACTED (blueprints/avatar.py)
  chat         — pending
  memory       — pending
  code         — pending
  media/codec  — pending
  agents       — pending
  security     — pending
  (all others) — pending (remaining in web_ui.py)
"""

from __future__ import annotations

from flask import Flask


def register_blueprints(app: Flask) -> None:
    """Register all extracted blueprints onto an existing Flask app.

    Called from web_ui.py after the Flask app object is created, so that
    extracted blueprints coexist with legacy routes during the transition.
    """
    from joi_companion.webapp.blueprints.avatar import avatar_bp
    app.register_blueprint(avatar_bp)
