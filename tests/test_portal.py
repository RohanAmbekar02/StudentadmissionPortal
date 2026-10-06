from io import BytesIO

import pytest

from app import create_app
from app.extensions import db
from app.models import ApplicationDocument, StudentApplication, User


@pytest.fixture
def app(tmp_path):
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "WTF_CSRF_ENABLED": False,
            "UPLOAD_FOLDER": str(tmp_path / "uploads"),
            "ADMIN_EMAIL": "admin@example.test",
        }
    )
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def create_user(email, role="student", password="correct-horse-battery"):
    user = User(full_name="Test Applicant", email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def login(client, email, password="correct-horse-battery"):
    return client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def test_registration_cannot_choose_admin_role(app, client):
    response = client.post(
        "/auth/register",
        data={
            "full_name": "New Student",
            "email": "student@example.com",
            "password": "a-strong-student-password",
            "confirm_password": "a-strong-student-password",
            "role": "admin",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email="student@example.com").one()
        assert user.role == "student"
    login(client, "student@example.com", "a-strong-student-password")
    assert client.get("/admin/dashboard").status_code == 403


def test_student_cannot_read_another_students_document(app, client):
    with app.app_context():
        owner = create_user("owner@example.test")
        other = create_user("other@example.test")
        application = StudentApplication(user_id=owner.id)
        db.session.add(application)
        db.session.flush()
        document = ApplicationDocument(
            application_id=application.id,
            document_type="identity",
            original_name="identity.pdf",
            stored_name="private-document.pdf",
        )
        db.session.add(document)
        db.session.commit()
        document_id = document.id

    login(client, "other@example.test")
    assert client.get(f"/student/documents/{document_id}").status_code == 403


def test_application_requires_all_documents_before_submission(app, client):
    with app.app_context():
        create_user("applicant@example.test")
    login(client, "applicant@example.test")
    assert client.get("/student/application").status_code == 200

    response = client.post(
        "/student/application",
        data={"full_name": "Test Applicant", "action": "save"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        application = StudentApplication.query.one()
        assert application.status == "draft"
        assert application.program is None

    form_data = {
        "full_name": "Test Applicant",
        "date_of_birth": "2003-04-05",
        "phone": "+1 555 0100",
        "program": "Computer Science",
        "address": "1 College Road",
        "action": "submit",
    }
    client.post("/student/application", data=form_data)
    with app.app_context():
        assert StudentApplication.query.one().status == "draft"

    for document_type in ("identity", "transcript", "photo"):
        response = client.post(
            "/student/documents",
            data={
                "document_type": document_type,
                "document": (BytesIO(b"%PDF-test"), f"{document_type}.pdf"),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert response.status_code == 200

    response = client.post(
        "/student/application",
        data=form_data,
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        application = StudentApplication.query.one()
        assert application.status == "submitted"
        assert len(application.documents) == 3


def test_admin_can_update_application_review(app, client):
    with app.app_context():
        student = create_user("student@example.test")
        application = StudentApplication(
            user_id=student.id,
            program="Biology",
            status="submitted",
        )
        create_user("admin@example.test", role="admin")
        db.session.add(application)
        db.session.commit()
        application_id = application.id

    login(client, "admin@example.test")
    assert client.get("/admin/dashboard").status_code == 200
    assert client.get("/admin/dashboard?q=Biology").status_code == 200
    assert client.get("/student/dashboard").status_code == 403
    response = client.post(
        f"/admin/applications/{application_id}/review",
        data={"status": "accepted", "review_note": "Welcome to the program."},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        application = db.session.get(StudentApplication, application_id)
        assert application.status == "accepted"
        assert application.review_note == "Welcome to the program."


def test_admin_can_see_student_saved_application(app, client):
    with app.app_context():
        student = create_user("saved@example.test")
        db.session.add(
            StudentApplication(
                user_id=student.id,
                program="Computer Science",
                status="draft",
            )
        )
        create_user("admin@example.test", role="admin")
        db.session.commit()

    login(client, "admin@example.test")
    response = client.get("/admin/dashboard?q=Computer")
    assert response.status_code == 200
    assert b"saved@example.test" in response.data
    assert b"Computer Science" in response.data
