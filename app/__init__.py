import os
from pathlib import Path

import click
from flask import Flask, render_template
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from config import Config
from .extensions import db

login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    from . import models  # noqa: F401
    from .routes.admin import admin_bp
    from .routes.auth import auth_bp
    from .routes.main import main_bp
    from .routes.student import student_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(student_bp, url_prefix="/student")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.cli.command("init-db")
    def init_db():
        """Create tables and provision the configured administrator."""
        from werkzeug.security import generate_password_hash

        from .models import User

        db.create_all()
        admin_email = os.getenv("ADMIN_EMAIL", "admin@admission.local").strip().lower()
        admin_password = os.getenv("ADMIN_PASSWORD")
        if admin_password:
            if len(admin_password) < 10 or len(admin_password) > 128:
                raise click.ClickException(
                    "ADMIN_PASSWORD must be between 10 and 128 characters."
                )
            admin = User.query.filter_by(email=admin_email).first()
            if admin is None:
                db.session.add(
                    User(
                        full_name="Portal Administrator",
                        email=admin_email,
                        password_hash=generate_password_hash(admin_password),
                        role="admin",
                    )
                )
                db.session.commit()
                click.echo(f"Administrator created: {admin_email}")
            elif admin.role != "admin":
                raise click.ClickException(
                    "The configured administrator email belongs to a non-admin account."
                )
            else:
                click.echo(f"Administrator already exists: {admin_email}")
        else:
            click.echo(
                "Tables created. Set ADMIN_PASSWORD in the environment to provision the administrator."
            )

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def upload_too_large(_error):
        from flask import flash, redirect, url_for

        limit_mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
        flash(f"The uploaded file is too large. The request limit is {limit_mb} MB.", "error")
        return redirect(url_for("student.application"))

    return app


@login_manager.user_loader
def load_user(user_id):
    from .models import User

    return db.session.get(User, int(user_id))
