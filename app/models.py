from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JobSource(Base):
    __tablename__ = "job_sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(200), default="")
    education: Mapped[str] = mapped_column(Text, default="")
    degrees: Mapped[str] = mapped_column(Text, default="")
    certifications: Mapped[str] = mapped_column(Text, default="")
    skills: Mapped[str] = mapped_column(Text, default="")
    experience: Mapped[str] = mapped_column(Text, default="")
    projects: Mapped[str] = mapped_column(Text, default="")
    preferred_titles: Mapped[str] = mapped_column(Text, default="")
    preferred_locations: Mapped[str] = mapped_column(Text, default="")
    desired_salary: Mapped[int] = mapped_column(Integer, default=60000)
    remote_preference: Mapped[str] = mapped_column(String(30), default="remote")
    excluded_companies: Mapped[str] = mapped_column(Text, default="")
    excluded_titles: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Resume(Base):
    __tablename__ = "resumes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(500))
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SearchPreference(Base):
    __tablename__ = "search_preferences"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    keywords: Mapped[str] = mapped_column(Text, default="")
    locations: Mapped[str] = mapped_column(Text, default="")
    min_salary: Mapped[int] = mapped_column(Integer, default=60000)
    remote_only: Mapped[bool] = mapped_column(Boolean, default=False)
    max_distance_miles: Mapped[int] = mapped_column(Integer, default=50)
    interval_hours: Mapped[float] = mapped_column(Float, default=4)
    enabled_sources: Mapped[str] = mapped_column(Text, default="greenhouse,lever")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source", "source_job_id", name="uq_source_job"),
        UniqueConstraint("canonical_url", name="uq_canonical_url"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    source: Mapped[str] = mapped_column(String(50), index=True)
    source_job_id: Mapped[str] = mapped_column(String(200), index=True)
    canonical_url: Mapped[str] = mapped_column(String(1000))
    title: Mapped[str] = mapped_column(String(500))
    employer: Mapped[str] = mapped_column(String(300))
    location: Mapped[str] = mapped_column(String(500), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remote: Mapped[bool] = mapped_column(Boolean, default=False)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    work_arrangement: Mapped[str] = mapped_column(String(30), default="")
    employment_type: Mapped[str] = mapped_column(String(100), default="")
    experience_requirements: Mapped[str] = mapped_column(Text, default="")
    required_qualifications: Mapped[str] = mapped_column(Text, default="")
    preferred_qualifications: Mapped[str] = mapped_column(Text, default="")
    last_verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active")
    match: Mapped["JobMatch | None"] = relationship(back_populates="job", uselist=False)


class CompanyWatchlist(Base):
    __tablename__ = "company_watchlist"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    company: Mapped[str] = mapped_column(String(300))
    career_url: Mapped[str] = mapped_column(String(1000), default="")
    ats_type: Mapped[str] = mapped_column(String(30), default="")
    ats_board: Mapped[str] = mapped_column(String(300), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    limitation: Mapped[str] = mapped_column(Text, default="")
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class JobMatch(Base):
    __tablename__ = "job_matches"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), unique=True)
    score: Mapped[int] = mapped_column(Integer, default=0)
    explanation: Mapped[str] = mapped_column(Text, default="")
    matching: Mapped[str] = mapped_column(Text, default="")
    missing: Mapped[str] = mapped_column(Text, default="")
    concerns: Mapped[str] = mapped_column(Text, default="")
    recommendation: Mapped[str] = mapped_column(String(100), default="")
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    job: Mapped[Job] = relationship(back_populates="match")


class SavedJob(Base):
    __tablename__ = "saved_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), unique=True)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ApplicationStatus(str, Enum):
    INTERESTED = "Interested"
    APPLIED = "Applied"
    ASSESSMENT = "Assessment"
    INTERVIEW = "Interview"
    FINAL_INTERVIEW = "Final Interview"
    OFFER = "Offer"
    REJECTED = "Rejected"
    WITHDRAWN = "Withdrawn"


class Application(Base):
    __tablename__ = "applications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), unique=True)
    application_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default=ApplicationStatus.INTERESTED.value)
    resume_version: Mapped[str] = mapped_column(String(36), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    follow_up_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    contact_name: Mapped[str] = mapped_column(String(200), default="")
    contact_email: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SearchRun(Base):
    __tablename__ = "search_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="running")
    discovered: Mapped[int] = mapped_column(Integer, default=0)
    new_jobs: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[str] = mapped_column(Text, default="")


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), unique=True)
    mode: Mapped[str] = mapped_column(String(30), default="immediate")
    outcome: Mapped[str] = mapped_column(String(30), default="queued")
    attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    details: Mapped[str] = mapped_column(Text, default="")
