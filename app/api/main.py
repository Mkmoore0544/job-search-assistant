from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database import ensure_sqlite_schema, get_db, init_db
from app.models import Application, CompanyWatchlist, Job, JobMatch, Profile, Resume, SavedJob, SearchPreference, SearchRun
from app.notifications.email import send_test_email
from app.scheduler.search_scheduler import configure_scheduler, run_search_async
from app.services.resume import MAX_UPLOAD_BYTES, extract_resume_text

app = FastAPI(title="AI Job Search Assistant", version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    init_db()
    ensure_sqlite_schema()
    db = next(get_db())
    try:
        if not db.scalar(select(Profile)):
            db.add(Profile(
                name="",
                education="Bachelor of Science in Software Engineering",
                degrees="Pursuing Master of Science in Computer Science",
                skills="Python, JavaScript, React, Node.js, Express, SQL, MySQL, REST APIs, Git, AWS, Docker",
                preferred_titles="Junior Software Developer, Software Engineer I, Backend Developer, Application Developer I, Junior Python Developer, Junior DevOps Engineer, Cloud Support Engineer, SOC Analyst I, Junior Cybersecurity Analyst, IT Analyst, Application Support Analyst, Junior Data Analyst, QA Engineer",
                preferred_locations="Remote in the United States, Texarkana, Texas",
                desired_salary=60000,
            ))
        if not db.scalar(select(SearchPreference)):
            db.add(SearchPreference(
                keywords="Junior Software Developer, Software Engineer I, Backend Developer, Application Developer I, Junior Python Developer, Junior DevOps Engineer, Cloud Support Engineer, SOC Analyst I, Junior Cybersecurity Analyst, IT Analyst, Application Support Analyst, Junior Data Analyst, QA Engineer",
                locations="Remote in United States, Texarkana TX",
                min_salary=60000,
                enabled_sources="remotive,greenhouse,lever,ashby",
                interval_hours=4,
            ))
        else:
            preference = db.scalar(select(SearchPreference))
            if preference and preference.enabled_sources in {"greenhouse,lever", ""}:
                preference.enabled_sources = "remotive,greenhouse,lever,ashby"
        watchlist_names = [
            "Lockheed Martin", "Boeing", "RTX", "Northrop Grumman",
            "Amazon", "Microsoft", "Optum", "Arkansas state government",
        ]
        if db.scalar(select(func.count(CompanyWatchlist.id))) == 0:
            for company in watchlist_names:
                db.add(CompanyWatchlist(
                    company=company,
                    limitation="No career URL or supported ATS board configured.",
                ))
        db.commit()
    finally:
        db.close()
    configure_scheduler()


@app.on_event("shutdown")
def shutdown() -> None:
    from app.scheduler.search_scheduler import scheduler
    if scheduler.running:
        scheduler.shutdown(wait=False)


@app.get("/health")
def health() -> dict[str, bool]:
    return {"status": True}


@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)) -> dict[str, int]:
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return {
        "total_jobs": db.scalar(select(func.count(Job.id))) or 0,
        "new_today": db.scalar(select(func.count(Job.id)).where(Job.discovered_at >= today)) or 0,
        "high_matches": db.scalar(select(func.count(JobMatch.id)).where(JobMatch.score >= 70)) or 0,
        "saved_jobs": db.scalar(select(func.count(SavedJob.id))) or 0,
        "applications": db.scalar(select(func.count(Application.id))) or 0,
    }


@app.get("/api/jobs")
def jobs(db: Session = Depends(get_db), limit: int = 100) -> list[dict[str, object]]:
    rows = db.scalars(select(Job).order_by(Job.discovered_at.desc()).limit(limit)).all()
    return [{
        "id": job.id,
        "title": job.title,
        "employer": job.employer,
        "location": job.location,
        "url": job.canonical_url,
        "remote": job.remote,
        "work_arrangement": job.work_arrangement,
        "employment_type": job.employment_type,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "source": job.source,
        "posted_at": job.posted_at.isoformat() if job.posted_at else None,
        "last_verified_at": job.last_verified_at.isoformat(),
        "status": job.status,
        "discovered_at": job.discovered_at.isoformat(),
        "score": job.match.score if job.match else None,
        "description": job.description[:1000],
    } for job in rows]


@app.post("/api/search")
async def manual_search(db: Session = Depends(get_db)) -> dict[str, object]:
    run = await run_search_async()
    return {"id": run.id, "status": run.status, "discovered": run.discovered, "new_jobs": run.new_jobs}


@app.post("/api/search/keywords")
async def keyword_search(
    keywords: str,
    location: str = "United States",
    db: Session = Depends(get_db),
) -> dict[str, object]:
    preference = db.scalar(select(SearchPreference))
    if preference:
        preference.keywords = keywords
        preference.locations = location
        db.commit()
    run = await run_search_async()
    return {"id": run.id, "status": run.status, "discovered": run.discovered, "new_jobs": run.new_jobs}


@app.post("/api/jobs/{job_id}/save")
def save_job(job_id: str, db: Session = Depends(get_db)) -> dict[str, bool]:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if not db.scalar(select(SavedJob).where(SavedJob.job_id == job_id)):
        db.add(SavedJob(job_id=job_id))
        db.commit()
    return {"saved": True}


@app.post("/api/jobs/{job_id}/dismiss")
def dismiss_job(job_id: str, db: Session = Depends(get_db)) -> dict[str, bool]:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    job.dismissed = True
    db.commit()
    return {"dismissed": True}


@app.get("/api/profile")
def get_profile(db: Session = Depends(get_db)) -> dict[str, object]:
    profile = db.scalar(select(Profile))
    if not profile:
        return {}
    return {column.name: getattr(profile, column.name) for column in Profile.__table__.columns if column.name not in {"id", "updated_at"}}


@app.put("/api/profile")
def update_profile(payload: dict[str, object], db: Session = Depends(get_db)) -> dict[str, bool]:
    profile = db.scalar(select(Profile))
    if not profile:
        profile = Profile()
        db.add(profile)
    allowed = {"name", "education", "degrees", "certifications", "skills", "experience", "projects", "preferred_titles", "preferred_locations", "desired_salary", "remote_preference", "excluded_companies", "excluded_titles"}
    for key, value in payload.items():
        if key in allowed:
            setattr(profile, key, value)
    db.commit()
    return {"updated": True}


@app.post("/api/resume")
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict[str, str]:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".docx"}:
        raise HTTPException(400, "Only PDF and DOCX files are allowed")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Resume exceeds 10 MB")
    upload_dir = Path("uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid4().hex}{suffix}"
    path = upload_dir / safe_name
    path.write_bytes(content)
    try:
        text = extract_resume_text(str(path))
    except Exception as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(400, str(exc))
    resume = Resume(filename=Path(file.filename).name, stored_path=str(path), extracted_text=text)
    db.add(resume)
    db.commit()
    return {"id": resume.id, "filename": resume.filename}


@app.get("/api/preferences")
def get_preferences(db: Session = Depends(get_db)) -> dict[str, object]:
    preference = db.scalar(select(SearchPreference))
    if not preference:
        return {}
    return {column.name: getattr(preference, column.name) for column in SearchPreference.__table__.columns if column.name != "id"}


@app.put("/api/preferences")
def update_preferences(payload: dict[str, object], db: Session = Depends(get_db)) -> dict[str, bool]:
    preference = db.scalar(select(SearchPreference))
    if not preference:
        preference = SearchPreference()
        db.add(preference)
    for key in {"keywords", "locations", "min_salary", "remote_only", "max_distance_miles", "interval_hours", "enabled_sources"}:
        if key in payload:
            setattr(preference, key, payload[key])
    db.commit()
    configure_scheduler()
    return {"updated": True}


@app.post("/api/email/test")
def test_email(recipient: str) -> dict[str, bool]:
    send_test_email(recipient)
    return {"sent": True}


@app.get("/api/watchlist")
def get_watchlist(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    rows = db.scalars(select(CompanyWatchlist).order_by(CompanyWatchlist.company)).all()
    return [{
        "id": row.id,
        "company": row.company,
        "career_url": row.career_url,
        "ats_type": row.ats_type,
        "ats_board": row.ats_board,
        "enabled": row.enabled,
        "limitation": row.limitation,
    } for row in rows]


@app.post("/api/watchlist")
def add_watchlist(payload: dict[str, object], db: Session = Depends(get_db)) -> dict[str, str]:
    company = str(payload.get("company", "")).strip()
    career_url = str(payload.get("career_url", "")).strip()
    if not company:
        raise HTTPException(400, "Company name is required")
    ats_type = ""
    ats_board = ""
    limitation = ""
    lower_url = career_url.lower()
    if "greenhouse.io" in lower_url:
        parts = career_url.rstrip("/").split("/")
        ats_type = "greenhouse"
        ats_board = parts[-1] if parts else ""
    elif "lever.co" in lower_url:
        parts = career_url.rstrip("/").split("/")
        ats_type = "lever"
        ats_board = parts[-1] if parts else ""
    elif "ashbyhq.com" in lower_url:
        parts = career_url.rstrip("/").split("/")
        ats_type = "ashby"
        ats_board = parts[-1] if parts else ""
    elif career_url:
        limitation = "Career page cannot be monitored through a supported authorized ATS integration."
    row = CompanyWatchlist(
        company=company,
        career_url=career_url,
        ats_type=ats_type,
        ats_board=ats_board,
        limitation=limitation,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "ats_type": ats_type}


@app.get("/api/search-history")
def search_history(db: Session = Depends(get_db), limit: int = 50) -> list[dict[str, object]]:
    rows = db.scalars(select(SearchRun).order_by(SearchRun.started_at.desc()).limit(limit)).all()
    return [{
        "id": row.id,
        "started_at": row.started_at.isoformat(),
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
        "status": row.status,
        "discovered": row.discovered,
        "new_jobs": row.new_jobs,
        "errors": row.errors,
    } for row in rows]


@app.get("/api/manual-search-links")
def manual_search_links(
    keywords: str | None = None,
    location: str = "Texarkana, Texas",
    db: Session = Depends(get_db),
) -> dict[str, str]:
    preference = db.scalar(select(SearchPreference))
    search_terms = (keywords or (preference.keywords if preference else "")).strip()
    if not search_terms:
        search_terms = "Junior Software Developer"
    return {
        "indeed": "https://www.indeed.com/jobs?" + urlencode({
            "q": search_terms,
            "l": location,
        }),
        "linkedin": "https://www.linkedin.com/jobs/search/?" + urlencode({
            "keywords": search_terms,
            "location": location,
        }),
    }


@app.get("/api/website-search")
def website_search(
    site: str,
    keywords: str,
    location: str = "United States",
) -> dict[str, str]:
    search_terms = keywords.strip()
    if not search_terms:
        raise HTTPException(400, "Keywords are required")
    normalized_site = site.strip().lower()
    if normalized_site == "indeed":
        url = "https://www.indeed.com/jobs?" + urlencode({"q": search_terms, "l": location})
    elif normalized_site == "linkedin":
        url = "https://www.linkedin.com/jobs/search/?" + urlencode({
            "keywords": search_terms,
            "location": location,
        })
    elif normalized_site == "glassdoor":
        url = "https://www.glassdoor.com/Job/jobs.htm?" + urlencode({
            "sc.keyword": search_terms,
            "locT": "C",
            "locId": "1",
        })
    elif normalized_site == "ziprecruiter":
        url = "https://www.ziprecruiter.com/jobs-search?" + urlencode({
            "search": search_terms,
            "location": location,
        })
    elif normalized_site == "dice":
        url = "https://www.dice.com/jobs?" + urlencode({
            "q": search_terms,
            "location": location,
        })
    else:
        raise HTTPException(400, "Unsupported website")
    return {"url": url}
