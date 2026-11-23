import hashlib
import json
import re
from datetime import datetime, timezone

from openai import OpenAI
from pydantic import ValidationError

from app.core.config import settings
from app.models import Profile
from app.schemas import MatchResult


def rules_match(profile: Profile | None, title: str, description: str, min_salary: int) -> MatchResult:
    text = f"{title}\n{description}".lower()
    skills = [item.strip().lower() for item in (profile.skills if profile else "").split(",") if item.strip()]
    matching = [item for item in skills if item in text]
    missing = []
    preferred_titles = [item.strip().lower() for item in (profile.preferred_titles if profile else "").split(",") if item.strip()]
    title_score = 30 if any(item in title.lower() for item in preferred_titles) else 10
    skill_score = min(60, len(matching) * 15)
    education_bonus = 10 if "software" in text or "computer" in text else 0
    score = min(100, title_score + skill_score + education_bonus)
    if not matching:
        missing = skills[:5]
    return MatchResult(
        score=score,
        matching=matching,
        missing=missing,
        concerns=["This is a rules-based estimate; AI evaluation was not used."],
        explanation=f"{len(matching)} profile skills appear in the listing.",
        recommendation="Strong potential match." if score >= 70 else "Consider if transferable experience applies.",
    )


async def ai_match(profile: Profile | None, title: str, employer: str, description: str) -> MatchResult:
    if not settings.openai_api_key:
        return rules_match(profile, title, description, profile.desired_salary if profile else 60000)
    profile_text = json.dumps({
        "name": profile.name if profile else "",
        "education": profile.education if profile else "",
        "skills": profile.skills if profile else "",
        "experience": profile.experience if profile else "",
        "projects": profile.projects if profile else "",
    })
    prompt = (
        "Analyze this external job listing against the profile. "
        "Never invent qualifications. Return JSON only.\n"
        f"Profile: {profile_text}\nEmployer: {employer}\nTitle: {title}\n"
        f"Listing:\n{description[:12000]}"
    )
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.responses.parse(
            model=settings.openai_model,
            input=[{"role": "system", "content": "You are a precise job compatibility analyzer."}, {"role": "user", "content": prompt}],
            text_format=MatchResult,
        )
        if response.output_parsed:
            return response.output_parsed
    except Exception:
        pass
    return rules_match(profile, title, description, profile.desired_salary if profile else 60000)
