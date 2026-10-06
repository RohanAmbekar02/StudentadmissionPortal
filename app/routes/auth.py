from email_validator import EmailNotValidError, validate_email
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        admin_email = current_app.config.get("ADMIN_EMAIL", "admin@admission.local").lower()
        error = None

        if not full_name or len(full_name) > 120:
            error = "Enter a name of 1 to 120 characters."
        elif email == admin_email:
            error = "That email address is reserved."
        else:
            try:
                email = validate_email(email, check_deliverability=False).normalized.lower()
            except EmailNotValidError:
                error = "Enter a valid email address."

        if not error and (len(password) < 10 or len(password) > 128):
            error = "Use a password between 10 and 128 characters."
        elif not error and password != confirm_password:
            error = "The passwords do not match."

        if error:
            flash(error, "error")
        else:
            user = User(full_name=full_name, email=email, role="student")
            user.set_password(password)
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("An account with that email address already exists.", "error")
            else:
                flash("Your student account is ready. Please sign in.", "success")
                return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first() if len(password) <= 128 else None
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("main.index"))
        flash("Email or password is incorrect.", "error")

    return render_template("auth/login.html")


@auth_bp.post("/logout")
def logout():
    if current_user.is_authenticated:
        logout_user()
    return redirect(url_for("auth.login"))
