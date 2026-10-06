from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from sqlalchemy import or_

from ..authz import role_required
from ..extensions import db
from ..models import ApplicationDocument, StudentApplication, User
from .student import APPLICATION_STATUSES

admin_bp = Blueprint("admin", __name__)
REVIEW_STATUSES = {"under_review", "needs_changes", "accepted", "rejected"}


@admin_bp.get("/")
@admin_bp.get("/dashboard")
@role_required("admin")
def dashboard():
    status_filter = request.args.get("status", "")
    search = request.args.get("q", "").strip()
    query = StudentApplication.query.join(StudentApplication.student)
    if status_filter in APPLICATION_STATUSES:
        query = query.filter(StudentApplication.status == status_filter)
    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                User.full_name.ilike(term),
                User.email.ilike(term),
                StudentApplication.program.ilike(term),
            )
        )
    pagination = query.order_by(StudentApplication.updated_at.desc()).paginate(
        page=request.args.get("page", 1, type=int), per_page=15, error_out=False
    )
    return render_template(
        "admin/dashboard.html",
        pagination=pagination,
        statuses=APPLICATION_STATUSES,
        status_filter=status_filter,
        search=search,
    )


@admin_bp.get("/applications/<int:application_id>")
@role_required("admin")
def application_detail(application_id):
    record = db.session.get(StudentApplication, application_id)
    if record is None:
        abort(404)
    return render_template(
        "admin/application_detail.html",
        application=record,
        statuses=APPLICATION_STATUSES,
        review_statuses=REVIEW_STATUSES,
    )


@admin_bp.post("/applications/<int:application_id>/review")
@role_required("admin")
def update_review(application_id):
    record = db.session.get(StudentApplication, application_id)
    if record is None:
        abort(404)
    if record.status == "draft":
        flash("A draft application cannot be reviewed before it is submitted.", "error")
        return redirect(url_for("admin.application_detail", application_id=record.id))
    new_status = request.form.get("status", "")
    note = request.form.get("review_note", "").strip()
    if new_status not in REVIEW_STATUSES:
        abort(400)
    if len(note) > 4000:
        flash("Review notes must be 4,000 characters or fewer.", "error")
        return redirect(url_for("admin.application_detail", application_id=record.id))
    record.status = new_status
    record.review_note = note or None
    db.session.commit()
    flash("Application review updated.", "success")
    return redirect(url_for("admin.application_detail", application_id=record.id))


@admin_bp.get("/documents/<int:document_id>")
@role_required("admin")
def download_document(document_id):
    document = db.session.get(ApplicationDocument, document_id)
    if document is None:
        abort(404)
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        document.stored_name,
        as_attachment=True,
        download_name=document.original_name,
    )
