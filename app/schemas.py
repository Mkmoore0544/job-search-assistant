from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    source: str
    source_job_id: str
    canonical_url: str
    title: str
    employer: str
    location: str = ""
    description: str = ""
    salary_min: int | None = None
    salary_max: int | None = None
    remote: bool = False
    posted_at: str | None = None
    updated_at: str | None = None
    work_arrangement: str = ""
    employment_type: str = ""
    experience_requirements: str = ""
    required_qualifications: str = ""
    preferred_qualifications: str = ""


class MatchResult(BaseModel):
    score: int = Field(ge=0, le=100)
    matching: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    explanation: str
    recommendation: str
