import httpx

from app.providers.base import JobProvider
from app.schemas import JobCreate


class AshbyProvider(JobProvider):
    name = "ashby"

    def __init__(self, boards: list[str]) -> None:
        self.boards = boards

    async def search(self, keywords: list[str], locations: list[str]) -> list[JobCreate]:
        jobs: list[JobCreate] = []
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            for board in self.boards:
                try:
                    response = await client.post(
                        f"https://api.ashbyhq.com/posting-api/job-board/{board}",
                        json={"includeCompensation": True},
                    )
                    response.raise_for_status()
                    for item in response.json().get("jobs", []):
                        title = str(item.get("title", ""))
                        description = str(item.get("descriptionPlain", "") or "")
                        text = f"{title} {description}".lower()
                        if keywords and not any(word.lower() in text for word in keywords):
                            continue
                        location = str(item.get("location", "") or "")
                        is_remote = "remote" in location.lower()
                        compensation = item.get("compensation") or {}
                        salary_min = salary_max = None
                        tiers = compensation.get("compensationTiers") or []
                        if tiers:
                            try:
                                salary_min = int(tiers[0].get("interval", {}).get("min"))
                                salary_max = int(tiers[0].get("interval", {}).get("max"))
                            except (TypeError, ValueError, KeyError):
                                pass
                        jobs.append(JobCreate(
                            source="ashby",
                            source_job_id=str(item["id"]),
                            canonical_url=str(item["jobUrl"]),
                            title=title,
                            employer=board,
                            location=location,
                            description=description,
                            remote=is_remote,
                            work_arrangement="remote" if is_remote else "",
                            employment_type=str(item.get("employmentType", "") or ""),
                            salary_min=salary_min,
                            salary_max=salary_max,
                            posted_at=item.get("publishedAt"),
                            updated_at=item.get("updatedAt"),
                        ))
                except (httpx.HTTPError, ValueError, KeyError):
                    continue
        return jobs
