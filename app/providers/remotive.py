import httpx

from app.providers.base import JobProvider
from app.schemas import JobCreate


class RemotiveProvider(JobProvider):
    name = "remotive"

    async def search(self, keywords: list[str], locations: list[str]) -> list[JobCreate]:
        jobs: list[JobCreate] = []
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            for keyword in keywords[:8]:
                try:
                    response = await client.get("https://remotive.com/api/remote-jobs", params={"search": keyword, "limit": 50})
                    response.raise_for_status()
                    for item in response.json().get("jobs", []):
                        title = str(item.get("title", ""))
                        description = str(item.get("description", ""))
                        text = f"{title} {description}".lower()
                        if keywords and not any(word.lower() in text for word in keywords):
                            continue
                        jobs.append(JobCreate(
                            source="remotive",
                            source_job_id=str(item["id"]),
                            canonical_url=str(item["url"]),
                            title=title,
                            employer=str(item.get("company_name", "")),
                            location=str(item.get("candidate_required_location", "")),
                            description=str(item.get("description", "")),
                            salary_min=None,
                            salary_max=None,
                            remote=True,
                            work_arrangement="remote",
                            employment_type=str(item.get("job_type", "")),
                            posted_at=item.get("publication_date"),
                        ))
                except (httpx.HTTPError, ValueError, KeyError):
                    continue
        return jobs
