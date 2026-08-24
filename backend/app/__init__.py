from __future__ import annotations

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from flask import Flask, g


load_dotenv()

DEFAULT_STUDENT_PASSWORD = os.environ.get("DEFAULT_STUDENT_PASSWORD", "123456")
DEFAULT_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD", "admin123")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _template_folder() -> str:
    return str(_project_root() / "frontend" / "templates")


def _static_folder() -> str:
    return str(_project_root() / "frontend" / "static")


def get_db():
    db = g.get("db")
    if db is None:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL is not configured")
        db = psycopg2.connect(database_url)
        g.db = db
    return db


def close_db(_exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def initials(name: str | None) -> str:
    if not name:
        return "?"
    parts = [part for part in str(name).strip().split() if part]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def nationality_flag(value: str | None) -> str:
    if not value:
        return ""
    normalized = str(value).strip().lower()
    flags = {
        "cambodia": "🇰🇭",
        "cambodai": "🇰🇭",
        "khmer": "🇰🇭",
        "lao": "🇱🇦",
        "laos": "🇱🇦",
        "vietnam": "🇻🇳",
        "viet nam": "🇻🇳",
        "việt nam": "🇻🇳",
        "thailand": "🇹🇭",
        "myanmar": "🇲🇲",
        "china": "🇨🇳",
        "korea": "🇰🇷",
        "japan": "🇯🇵",
        "philippines": "🇵🇭",
    }
    return flags.get(normalized, "🌏")


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=_template_folder(),
        static_folder=_static_folder(),
    )
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "ktx-portal-dev-secret")
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    app.jinja_env.filters["initials"] = initials
    app.jinja_env.filters["nationality_flag"] = nationality_flag

    app.teardown_appcontext(close_db)

    from app.auth import bp as auth_bp
    from app.routes import admin, bills, main, reports, rooms, scholarship

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(main.bp)
    app.register_blueprint(rooms.bp)
    app.register_blueprint(bills.bp)
    app.register_blueprint(reports.bp)
    app.register_blueprint(scholarship.bp)
    app.register_blueprint(admin.bp, url_prefix="/admin")

    # One-time migration: wipe old shared default passwords from DB.
    # Resets every student still using 123@ktxquanly123 / 123456 to their passport number.
    with app.app_context():
        _ensure_bills_unit_rate_column()

    return app


def _ensure_bills_unit_rate_column():
    """Ensure bills.unit_rate exists so custom rates can be stored and displayed."""
    try:
        conn = psycopg2.connect(os.environ.get("DATABASE_URL", ""))
        cur = conn.cursor()
        cur.execute("""
            ALTER TABLE bills
            ADD COLUMN IF NOT EXISTS unit_rate INT
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[KTX] unit_rate migration skipped: {e}")