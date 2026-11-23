from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.providers.base import JobProvider
from app.schemas import JobCreate


class AdzunaProvider(JobProvider):
    name = "adzuna"

    async def search(self, keywords: list[str], locations: list[str]) -> list[JobCreate]:
        if not settings.adzuna_app_id or not settings.adzuna_app_key:
            return []
        jobs: list[JobCreate] = []
        async with httpx.AsyncClient(timeout=20) as client:
            for keyword in keywords[:8]:
                location = "Arkansas" if not locations else locations[0]
                try:
                    url = f"https://api.adzuna.com/v1/api/jobs/{settings.adzuna_country}/search/1"
                    response = await client.get(url, params={
                        "app_id": settings.adzuna_app_id,
                        "app_key": settings.adzuna_app_key,
                        "what": keyword,
                        "where": location,
                        "results_per_page": 50,
                        "content_type": "application/json",
                    })
                    response.raise_for_status()
                    for item in response.json().get("results", []):
                        salary_min = int(item["salary_min"]) if item.get("salary_min") else None
                        salary_max = int(item["salary_max"]) if item.get("salary_max") else None
                        location_name = str(item.get("location", {}).get("display_name", ""))
                        title = str(item.get("title", ""))
                        description = str(item.get("description", ""))
                        remote = "remote" in f"{title} {description}".lower()
                        created = item.get("created")
                        jobs.append(JobCreate(
                            source="adzuna",
                            source_job_id=str(item["id"]),
                            canonical_url=str(item["redirect_url"]),
                            title=title,
                            employer=str(item.get("company", {}).get("display_name", "")),
                            location=location_name,
                            description=description,
                            salary_min=salary_min,
                            salary_max=salary_max,
                            remote=remote,
                            work_arrangement="remote" if remote else "",
                            posted_at=created,
                        ))
                except (httpx.HTTPError, ValueError, KeyError):
                    continue
        return jobs
