from flask import Blueprint, redirect, url_for
from flask_login import current_user

main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def index():
    if current_user.is_authenticated:
        endpoint = "admin.dashboard" if current_user.is_admin else "student.dashboard"
        return redirect(url_for(endpoint))
    return redirect(url_for("auth.login"))
