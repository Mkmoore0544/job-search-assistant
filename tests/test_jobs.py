from app.models import Profile
from app.schemas import JobCreate
from app.services.jobs import is_duplicate, normalize_url, parse_posted_at, remote_eligible, salary_meets
from app.ai.matching import rules_match


def test_normalize_url():
    assert normalize_url("https://example.com/job#apply") == "https://example.com/job"


def test_salary_filter():
    assert salary_meets("Salary: $70,000 per year", 60000)
    assert not salary_meets("Salary: $55,000 per year", 60000)
    assert salary_meets("Salary not disclosed", 60000)


def test_remote_eligibility():
    assert remote_eligible("Anywhere in US", True)
    assert remote_eligible("Texarkana, Texas", False)
    assert not remote_eligible("Seattle, Washington", False)


def test_duplicate_detection(db_session):
    incoming = JobCreate(
        source="greenhouse",
        source_job_id="123",
        canonical_url="https://example.com/jobs/123",
        title="Junior Python Developer",
        employer="Example",
    )
    assert is_duplicate(db_session, incoming) is None


def test_rules_matching():
    profile = Profile(
        education="Bachelor of Science in Software Engineering",
        skills="Python, SQL, REST APIs",
        preferred_titles="Junior Python Developer",
    )
    result = rules_match(profile, "Junior Python Developer", "Python SQL REST APIs position", 60000)
    assert result.score >= 70
    assert "python" in result.matching
