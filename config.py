import os
import secrets
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@admission.local").strip().lower()
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:password@localhost/admission_portal?charset=utf8mb4",
    )
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }
    if os.getenv("DB_SSL_CA"):
        SQLALCHEMY_ENGINE_OPTIONS["connect_args"] = {
            "ssl_ca": os.getenv("DB_SSL_CA"),
            "ssl_verify_cert": True,
            "ssl_verify_identity": True,
        }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 8 * 1024 * 1024))
    UPLOAD_FOLDER = str(BASE_DIR / "instance" / "uploads")
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
