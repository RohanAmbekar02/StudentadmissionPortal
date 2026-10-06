from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename

from ..authz import role_required
from ..extensions import db
from ..models import ApplicationDocument, StudentApplication

student_bp = Blueprint("student", __name__)
DOCUMENT_TYPES = {
    "identity": "Identity proof",
    "transcript": "Academic transcript",
    "photo": "Student photo",
}
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
EDITABLE_STATUSES = {"draft", "needs_changes"}
APPLICATION_STATUSES = {
    "draft": "Draft",
    "submitted": "Submitted",
    "under_review": "Under review",
    "needs_changes": "Changes requested",
    "accepted": "Accepted",
    "rejected": "Rejected",
}


def get_or_create_application():
    application = StudentApplication.query.filter_by(user_id=current_user.id).first()
    if application is None:
        application = StudentApplication(user_id=current_user.id)
        db.session.add(application)
        db.session.commit()
    return application


@student_bp.get("/dashboard")
@role_required("student")
def dashboard():
    application = StudentApplication.query.filter_by(user_id=current_user.id).first()
    return render_template(
        "student/dashboard.html",
        application=application,
        statuses=APPLICATION_STATUSES,
    )


@student_bp.route("/application", methods=["GET", "POST"])
@role_required("student")
def application():
    record = get_or_create_application()
    if record.status not in EDITABLE_STATUSES:
        flash("Your application is locked while it is being reviewed or after a decision.", "info")
        return redirect(url_for("student.dashboard"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        program = request.form.get("program", "").strip()
        birth_date_text = request.form.get("date_of_birth", "").strip()
        action = request.form.get("action", "save")
        error = None

        if action not in {"save", "submit"}:
            error = "Invalid application action."
        elif not full_name or len(full_name) > 120:
            error = "Enter your full name (up to 120 characters)."
        elif len(phone) > 30:
            error = "Use a phone number with no more than 30 characters."
        elif len(address) > 4000:
            error = "Use an address with no more than 4,000 characters."
        elif len(program) > 120:
            error = "Use a program name with no more than 120 characters."

        birth_date = None
        if not error and birth_date_text:
            try:
                birth_date = date.fromisoformat(birth_date_text)
                if birth_date >= date.today():
                    error = "Date of birth must be in the past."
            except ValueError:
                error = "Enter a valid date of birth."

        if action == "submit" and not error and (
            not birth_date
            or not phone
            or not address
            or not program
        ):
            error = "Complete all required fields before submitting."
        if action == "submit" and not error:
            existing_types = {document.document_type for document in record.documents}
            missing = set(DOCUMENT_TYPES) - existing_types
            if missing:
                error = "Upload an identity proof, academic transcript, and student photo before submitting."

        if error:
            flash(error, "error")
        else:
            current_user.full_name = full_name
            record.phone = phone or None
            record.address = address or None
            record.program = program or None
            record.date_of_birth = birth_date
            if action == "submit":
                record.status = "submitted"
                record.submitted_at = datetime.now(timezone.utc)
            db.session.commit()
            flash(
                "Application submitted successfully." if action == "submit" else "Application saved as a draft.",
                "success",
            )
            return redirect(url_for("student.dashboard"))

    return render_template(
        "student/application_form.html",
        application=record,
        document_types=DOCUMENT_TYPES,
    )


@student_bp.post("/documents")
@role_required("student")
def upload_document():
    record = get_or_create_application()
    if record.status not in EDITABLE_STATUSES:
        flash("Documents cannot be changed while the application is being reviewed.", "error")
        return redirect(url_for("student.dashboard"))

    document_type = request.form.get("document_type", "")
    upload = request.files.get("document")
    original_name = secure_filename(upload.filename or "") if upload else ""
    suffix = Path(original_name).suffix.lower().lstrip(".")
    if document_type not in DOCUMENT_TYPES:
        flash("Choose a valid document type.", "error")
    elif not upload or not original_name or suffix not in ALLOWED_EXTENSIONS:
        flash("Choose a PDF, PNG, JPG, or JPEG file.", "error")
    else:
        stored_name = f"{uuid4().hex}.{suffix}"
        destination = Path(current_app.config["UPLOAD_FOLDER"]) / stored_name
        upload.save(destination)
        document = ApplicationDocument.query.filter_by(
            application_id=record.id, document_type=document_type
        ).first()
        old_stored_name = document.stored_name if document else None
        if document is None:
            document = ApplicationDocument(
                application_id=record.id,
                document_type=document_type,
                original_name=original_name[:255],
                stored_name=stored_name,
            )
            db.session.add(document)
        else:
            document.original_name = original_name[:255]
            document.stored_name = stored_name
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            destination.unlink(missing_ok=True)
            current_app.logger.exception("Could not save application document metadata.")
            flash("The document could not be saved. Please try again.", "error")
        else:
            if old_stored_name:
                (Path(current_app.config["UPLOAD_FOLDER"]) / old_stored_name).unlink(missing_ok=True)
            flash(f"{DOCUMENT_TYPES[document_type]} uploaded.", "success")
    return redirect(url_for("student.application"))


@student_bp.get("/documents/<int:document_id>")
@role_required("student")
def download_document(document_id):
    document = db.session.get(ApplicationDocument, document_id)
    if document is None:
        abort(404)
    if document.application.user_id != current_user.id:
        abort(403)
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        document.stored_name,
        as_attachment=True,
        download_name=document.original_name,
    )
