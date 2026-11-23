from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.matching import ai_match
from app.core.config import settings
from app.models import Job, JobMatch, Profile, SearchPreference, SearchRun
from app.schemas import JobCreate
from difflib import SequenceMatcher


def parse_posted_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def is_duplicate(db: Session, incoming: JobCreate) -> Job | None:
    existing = db.scalar(select(Job).where(
        ((Job.source == incoming.source) & (Job.source_job_id == incoming.source_job_id))
        | (Job.canonical_url == incoming.canonical_url)
    ))
    if existing:
        return existing
    normalized_title = re.sub(r"[^a-z0-9]+", " ", incoming.title.lower()).strip()
    normalized_location = re.sub(r"[^a-z0-9]+", " ", incoming.location.lower()).strip()
    candidates = db.scalars(select(Job).where(Job.employer == incoming.employer)).all()
    for candidate in candidates:
        candidate_title = re.sub(r"[^a-z0-9]+", " ", candidate.title.lower()).strip()
        candidate_location = re.sub(r"[^a-z0-9]+", " ", candidate.location.lower()).strip()
        title_ratio = SequenceMatcher(None, normalized_title, candidate_title).ratio()
        location_ratio = SequenceMatcher(None, normalized_location, candidate_location).ratio()
        if title_ratio >= 0.92 and (not normalized_location or not candidate_location or location_ratio >= 0.75):
            return candidate
    return None


def normalize_url(url: str) -> str:
    return url.strip().split("#")[0].rstrip("/")


def salary_meets(text: str, minimum: int) -> bool:
    numbers = [int(value.replace(",", "")) for value in re.findall(r"\$?([\d]{2,3}[,\d]*)", text)]
    if not numbers:
        return True
    relevant = [value for value in numbers if value >= 30000]
    return not relevant or max(relevant) >= minimum


def remote_eligible(location: str, remote: bool) -> bool:
    if remote:
        return True
    text = location.lower()
    return "texarkana" in text or "arkansas" in text


async def persist_and_match(db: Session, incoming: JobCreate) -> tuple[Job, bool]:
    existing = is_duplicate(db, incoming)
    new_job = existing is None
    if existing:
        existing.title = incoming.title
        existing.location = incoming.location
        existing.description = incoming.description
        existing.salary_min = incoming.salary_min
        existing.salary_max = incoming.salary_max
        existing.remote = incoming.remote
        existing.work_arrangement = incoming.work_arrangement
        existing.employment_type = incoming.employment_type
        existing.experience_requirements = incoming.experience_requirements
        existing.required_qualifications = incoming.required_qualifications
        existing.preferred_qualifications = incoming.preferred_qualifications
        existing.status = "active"
        existing.last_verified_at = datetime.now(timezone.utc)
        existing.last_updated_at = parse_posted_at(incoming.updated_at)
        existing.updated_at = datetime.now(timezone.utc)
        job = existing
    else:
        job = Job(
            source=incoming.source,
            source_job_id=incoming.source_job_id,
            canonical_url=normalize_url(incoming.canonical_url),
            title=incoming.title,
            employer=incoming.employer,
            location=incoming.location,
            description=incoming.description,
            salary_min=incoming.salary_min,
            salary_max=incoming.salary_max,
            remote=incoming.remote,
            posted_at=parse_posted_at(incoming.posted_at),
            work_arrangement=incoming.work_arrangement,
            employment_type=incoming.employment_type,
            experience_requirements=incoming.experience_requirements,
            required_qualifications=incoming.required_qualifications,
            preferred_qualifications=incoming.preferred_qualifications,
            last_verified_at=datetime.now(timezone.utc),
            last_updated_at=parse_posted_at(incoming.updated_at),
        )
        db.add(job)
        db.flush()

    if job.match is None:
        profile = db.scalar(select(Profile))
        preference = db.scalar(select(SearchPreference))
        minimum = preference.min_salary if preference else (profile.desired_salary if profile else 60000)
        if salary_meets(incoming.description, minimum) and remote_eligible(incoming.location, incoming.remote):
            result = await ai_match(profile, incoming.title, incoming.employer, incoming.description)
        else:
            result = await ai_match(profile, incoming.title, incoming.employer, incoming.description)
        db.add(JobMatch(
            job_id=job.id,
            score=result.score,
            explanation=result.explanation,
            matching="\n".join(result.matching),
            missing="\n".join(result.missing),
            concerns="\n".join(result.concerns),
            recommendation=result.recommendation,
        ))
    db.commit()
    db.refresh(job)
    return job, new_job
