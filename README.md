# Online Student Admission Portal

A role-based admissions portal built with Python, Flask, server-rendered HTML/CSS, and MySQL. Students can create accounts, prepare an application, upload supporting documents, submit it, and follow its review status. An administrator can find applications, download their documents, and send decisions or feedback.

## Features

- Separate student and administrator dashboards with server-enforced role checks.
- Student self-registration always creates a `student` account; a submitted role is ignored.
- One administrator identity, configured using `ADMIN_EMAIL`, provisioned with a password from `ADMIN_PASSWORD`. The password is hashed, not stored as plain text.
- Student application drafts with program, contact, address, and date-of-birth information.
- PDF/JPG/PNG document uploads for identity proof, academic transcript, and student photo.
- Private document storage outside the public static directory, with owner/admin-only download routes.
- Submission checks for required fields and all three required document types.
- Admin application search, status filter, paginated results, review notes, and status decisions.
- CSRF protection, password hashing, prepared ORM queries, upload-name randomization, and request size limits.
- SQLite can be selected for local tests; the application defaults to a MySQL connection.

## Requirements

- Python 3.10 or newer
- MySQL 8.x (or a compatible MySQL server)

## Run on Windows

Open PowerShell in this project folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set a long random `SECRET_KEY`, the MySQL `DATABASE_URL`, and a strong `ADMIN_PASSWORD`. Create the database once in MySQL:

```sql
CREATE DATABASE admission_portal
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

The default `DATABASE_URL` in `.env.example` is:

```text
mysql+pymysql://root:your-password@localhost/admission_portal?charset=utf8mb4
```

Replace the username and password with your MySQL credentials. Do not commit `.env`; it is ignored by Git.

Create the tables and provision the administrator, then start the development server:

```powershell
flask --app run.py init-db
flask --app run.py run --debug
```

Open <http://127.0.0.1:5000>. Students register through **Create account**. The administrator signs in with the configured `ADMIN_EMAIL` and `ADMIN_PASSWORD`.

The `init-db` command creates the administrator only when that email does not already exist. It does not reset an existing administrator's password. If no `ADMIN_PASSWORD` is configured, it creates tables only and reports that the administrator was not provisioned.

## Environment variables

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Flask session and CSRF signing key. Set a unique, random value. |
| `DATABASE_URL` | SQLAlchemy database URL; MySQL is the default. |
| `DB_SSL_CA` | Optional CA bundle path. Set it to enable certificate and hostname verification for remote MySQL-compatible databases. |
| `ADMIN_EMAIL` | Reserved administrator login identity. Defaults to `admin@admission.local`. |
| `ADMIN_PASSWORD` | Initial administrator password. Set before running `init-db`. |
| `MAX_CONTENT_LENGTH` | Maximum request/upload size in bytes. Defaults to 8 MiB. |
| `FLASK_DEBUG` | Set to `1` only for local development. |

## Project structure

```text
online-student-admission-portal/
├── app/
│   ├── __init__.py              # App factory, extensions, CLI setup
│   ├── authz.py                 # Server-side role authorization
│   ├── extensions.py            # SQLAlchemy instance
│   ├── models.py                # User, StudentApplication, ApplicationDocument
│   ├── routes/
│   │   ├── admin.py             # Admin search, review, and document download
│   │   ├── auth.py              # Registration, login, and logout
│   │   ├── main.py              # Role-aware home redirect
│   │   └── student.py           # Student application and document handling
│   ├── static/css/styles.css    # Responsive portal styling
│   └── templates/
│       ├── admin/               # Admin list and application review
│       ├── auth/                # Login and registration
│       ├── errors/              # 403 and 404 pages
│       ├── student/             # Dashboard and application form
│       └── base.html            # Shared layout and navigation
├── tests/
│   └── test_portal.py           # Role, submission, and access tests
├── .env.example                 # Local configuration template
├── .gitignore
├── config.py
├── render.yaml                  # Render web service deployment blueprint
├── requirements.txt
└── run.py
```

## Role and application flow

1. A student creates an account. The server assigns the `student` role; registration never accepts role selection.
2. A student fills in the application, saves drafts, and uploads all required document categories.
3. Submitting requires a date of birth, phone, address, program, and all three document types.
4. Submitted applications appear in the administrator dashboard. The admin can review details/files and set `Under review`, `Changes requested`, `Accepted`, or `Rejected`, optionally with a note. Draft applications cannot be given a decision.
5. Applications are editable only as a draft or after changes are requested. Students can see the latest status and admin note on their dashboard.

## Free demo deployment (Render + TiDB Cloud Starter)

The included `render.yaml` prepares a Render web service. TiDB Cloud Starter is MySQL-protocol compatible, and the app uses the same SQLAlchemy/PyMySQL database layer. Free-plan quotas and eligibility can change; check both providers' current account terms before deploying.

1. Create a GitHub repository and push this project. Keep `.env` out of Git; `.gitignore` excludes it. Never put database passwords or the administrator password in the repository.
2. Create a TiDB Cloud Starter instance and generate its database password. In its **Connect** dialog, copy the public endpoint, username, port, and database name. Follow TiDB's TLS instructions; its public endpoint requires TLS.
3. Create a Render account and create a new **Blueprint** from the GitHub repository. Render reads `render.yaml`. Set the prompted `DATABASE_URL` using the TiDB connection details. Use SQLAlchemy's PyMySQL URL form:

   ```text
   mysql+pymysql://USERNAME:PASSWORD@HOST:4000/DATABASE
   ```

   Use the username and database values exactly as shown by TiDB, including its required account/cluster prefix. URL-encode special characters in the password if needed. Set `ADMIN_EMAIL` and a strong `ADMIN_PASSWORD` in Render's environment settings; Render generates `SECRET_KEY`.
4. In the TiDB public endpoint firewall, allow the outbound IP ranges shown for the Render service (**Render Dashboard → service → Connect → Outbound**). Do not open the database to all IP addresses. Use the matching Render/TiDB regions where possible. The service may need a redeploy after the allowlist is updated.
5. On startup, `init-db` creates the application tables and the configured administrator if they do not already exist. Open the Render service URL. Students can register and save applications; the admin signs in with the configured admin credentials and sees saved applications in the admin dashboard.

Student profile/application fields and review statuses are stored in TiDB, so they remain available to the admin across web-service restarts. **Uploaded documents are still saved on the web service's local filesystem**, which is temporary on Render's free plan; uploaded files can be lost after a restart or redeploy. Use only dummy/test documents until durable object storage is added. This free setup is for a demonstration, not real admissions data.

The existing local MySQL database is not copied to TiDB automatically. The remote deployment begins with its own database; new accounts and applications created on the deployed site are stored there.

## Tests

Install requirements, then run:

```powershell
python -m pytest
```

Tests use an isolated SQLite database and a temporary upload directory; no MySQL server is needed for them.

## Production notes

This is a clean starter project, not a production deployment recipe. Before deployment, configure a proper secret and HTTPS, use a managed MySQL account with least privilege, back up the database and private upload directory, add database migrations (for example, Flask-Migrate/Alembic) before changing deployed schemas, and configure a production WSGI server. Do not expose Flask's development server or debug mode to the internet. For sensitive real-world student data, review applicable privacy, retention, and records-handling requirements.
