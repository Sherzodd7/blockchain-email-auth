# app/__init__.py — Flask application factory
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask      import Flask, send_from_directory
from flask_cors import CORS

from config               import Config
from app.database         import init_db
from app.crypto           import generate_keys
from app.routes           import email_bp
from app.utils.logger     import log


def create_app(config: type = Config) -> Flask:
    """
    Flask application factory.
    Usage:
        app = create_app()
        app.run(...)
    """
    app = Flask(
        __name__,
        static_folder  = os.path.join(os.path.dirname(__file__), "..", "frontend"),
        static_url_path= "",
    )
    app.config.from_object(config)

    # ── CORS (allow frontend on any origin in dev) ────────────────────────
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # ── Bootstrap ──────────────────────────────────────────────────────────
    _bootstrap(config)

    # ── Blueprints ─────────────────────────────────────────────────────────
    app.register_blueprint(email_bp)

    # ── Serve frontend SPA ─────────────────────────────────────────────────
    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/<path:path>")
    def static_files(path):
        return send_from_directory(app.static_folder, path)

    # ── Global error handlers ──────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        from flask import jsonify
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        from flask import jsonify
        log.error("Unhandled 500: %s", e)
        return jsonify({"error": "Internal server error"}), 500

    log.info("Flask app created — debug=%s  port=%s", config.DEBUG, config.PORT)
    return app


def _bootstrap(config: type) -> None:
    """One-time setup: DB init + RSA key generation."""
    # Ensure database directory exists
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    init_db()

    # Generate RSA keys if they don't exist yet
    if not os.path.exists(config.PRIVATE_KEY_PATH):
        log.info("First run — generating RSA key pair…")
        generate_keys()
        