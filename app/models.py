from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utc_now():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    application = db.relationship(
        "StudentApplication",
        back_populates="student",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"


class StudentApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    date_of_birth = db.Column(db.Date, nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    address = db.Column(db.Text, nullable=True)
    program = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(30), nullable=False, default="draft", index=True)
    review_note = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    student = db.relationship("User", back_populates="application")
    documents = db.relationship(
        "ApplicationDocument", back_populates="application", cascade="all, delete-orphan"
    )


class ApplicationDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(
        db.Integer, db.ForeignKey("student_application.id", ondelete="CASCADE"), nullable=False
    )
    document_type = db.Column(db.String(30), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(80), unique=True, nullable=False)
    uploaded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    application = db.relationship("StudentApplication", back_populates="documents")
    __table_args__ = (
        db.UniqueConstraint("application_id", "document_type", name="uq_application_document_type"),
    )
