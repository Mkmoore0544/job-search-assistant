import httpx

from app.providers.base import JobProvider
from app.schemas import JobCreate


class LeverProvider(JobProvider):
    name = "lever"

    def __init__(self, sites: list[str]) -> None:
        self.sites = sites

    async def search(self, keywords: list[str], locations: list[str]) -> list[JobCreate]:
        jobs: list[JobCreate] = []
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            for site in self.sites:
                try:
                    response = await client.get(f"https://api.lever.co/v0/postings/{site}", params={"mode": "json"})
                    response.raise_for_status()
                    for item in response.json():
                        title = str(item.get("text", ""))
                        description = str(item.get("descriptionPlain", "") or "")
                        if keywords and not any(word.lower() in f"{title} {description}".lower() for word in keywords):
                            continue
                        categories = item.get("categories") or {}
                        location = str(categories.get("location", ""))
                        jobs.append(JobCreate(
                            source="lever",
                            source_job_id=str(item["id"]),
                            canonical_url=str(item["hostedUrl"]),
                            title=title,
                            employer=str(item.get("company", "") or site),
                            location=location,
                            description=description,
                            remote="remote" in location.lower(),
                            work_arrangement="remote" if "remote" in location.lower() else "",
                            posted_at=str(item.get("createdAt")) if item.get("createdAt") else None,
                        ))
                except (httpx.HTTPError, ValueError, KeyError):
                    continue
        return jobs
