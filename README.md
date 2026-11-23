# AI Job Search Assistant

A local-first FastAPI and Streamlit application for collecting authorized public job listings, matching them against a resume/profile, tracking applications, and sending notifications.

## Features

- USAJOBS, Greenhouse, and Lever provider integrations
- Scheduled and manual searches with duplicate detection
- Rules-based matching with optional OpenAI structured analysis
- Resume upload for PDF and DOCX
- Streamlit dashboard for jobs, applications, profile, preferences, and settings
- SQLite persistence and SQLAlchemy/Alembic support
- SMTP test email support
- Docker Compose deployment option

## Windows setup

1. Install Python 3.12.
2. From PowerShell in this folder:

```powershell
py -3.12 -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python -c "from app.database import init_db; init_db()"
```

3. Start both services:

```powershell
.\scripts\start.ps1
```

Or start manually:

```powershell
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
python -m streamlit run app/dashboard/app.py --server.address 127.0.0.1
```

- API: http://127.0.0.1:8000
- API docs: http://127.0.0.1:8000/docs
- Dashboard: http://127.0.0.1:8501

## Configuration

Copy `.env.example` to `.env`.

Required for all features:

- `DATABASE_URL`: SQLite default is `sqlite:///./data/jobs.db`
- `GREENHOUSE_BOARDS`: comma-separated authorized Greenhouse board tokens
- `LEVER_BOARDS`: comma-separated authorized Lever site tokens

Optional credential-backed integrations:

- `USAJOBS_API_KEY`
- `USAJOBS_USER_AGENT`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `EMAIL_FROM`
- `NOTIFY_EMAIL`

The default Greenhouse and Lever source lists are empty unless configured. USAJOBS is skipped without an API key. Matching uses deterministic rules when OpenAI is unavailable.

## Resume

Upload a PDF or DOCX resume from **Resume and Profile**. Files are stored in `uploads/` and extracted text is kept in SQLite. The application never invents missing qualifications.

## Tests

```powershell
pytest -q
python scripts/smoke_test.py
```

The test suite uses mocked/in-memory data and does not require external API credentials.

## Docker

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Docker publishes FastAPI and Streamlit only on `127.0.0.1`.

## Database migrations

The application initializes SQLAlchemy tables directly. Alembic configuration is provided for future migrations:

```powershell
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

## Data safety

- Store secrets only in `.env`
- Back up `data/jobs.db`, `uploads/`, and `.env`
- Resume uploads are restricted to PDF/DOCX and 10 MB
- External provider text is treated as untrusted data
- Run only on localhost until authentication and HTTPS are added
