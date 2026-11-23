# Implementation Status

## Completed

- Added Remotive, Adzuna, and Ashby provider integrations.
- Added richer normalized job fields and duplicate similarity detection.
- Added Company Watchlist persistence, API endpoints, ATS URL detection, and dashboard management.
- Added search-history API and dashboard page.
- Added watchlist-backed Greenhouse, Lever, and Ashby searches.
- Added lawful one-click public website searches for Indeed, LinkedIn, Glassdoor, ZipRecruiter, and Dice.

- FastAPI backend with health, dashboard, jobs, search, profile, resume, preference, and test-email endpoints
- Streamlit dashboard pages and navigation
- SQLAlchemy models for jobs, profiles, resumes, preferences, matches, saved jobs, applications, searches, and notifications
- Greenhouse, Lever, and USAJOBS provider modules
- Rules-based job matching and optional OpenAI response parsing with fallback
- PDF/DOCX resume text extraction
- Background APScheduler search scheduling with overlap lock
- SQLite initialization and Alembic configuration
- PowerShell and Docker startup
- SMTP test email support
- Unit and API tests

## Tested locally

Verified on Windows with Python 3.14:

- `pytest -q`: 7 tests passed
- `python scripts/smoke_test.py`: passed
- SQLite database initialization: passed
- FastAPI `/health`: returned `{"status": true}`
- Streamlit dashboard: HTTP 200 at `http://127.0.0.1:8501`

External API behavior is intentionally mocked or credential-gated.

## Requires credentials or external configuration

- USAJOBS API key and user agent
- Greenhouse board identifiers
- Lever site identifiers
- OpenAI API key
- SMTP account and notification recipient

## Known limitations

- Initial application is single-user and has no authentication
- Application Tracker is model/API capable but has a limited Streamlit UI
- Saved Jobs uses the Job Explorer rather than a fully separate live query
- Search History and notification history are not fully rendered in Streamlit
- AI chat assistant is database-aware for ranking/search but does not yet implement all natural-language tool actions
- Email alerts, immediate/daily/weekly policies, and notification deduplication need further implementation
- Live providers need credentials/sample board lists and network testing
- Alembic initial migration should be generated in an initialized environment

## Recommended improvements

1. Add authentication and per-user isolation.
2. Complete application tracker UI and CSV export.
3. Add notification batching and delivery retry records.
4. Add structured AI tool-calling and confirmation workflows.
5. Add provider fixtures and live integration tests.
6. Add PostgreSQL and object-storage adapters.
7. Add HTTPS reverse proxy and secret management before public deployment.
