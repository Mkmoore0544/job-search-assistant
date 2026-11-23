import html

import httpx

from app.providers.base import JobProvider
from app.schemas import JobCreate


class GreenhouseProvider(JobProvider):
    name = "greenhouse"

    def __init__(self, boards: list[str]) -> None:
        self.boards = boards

    async def search(self, keywords: list[str], locations: list[str]) -> list[JobCreate]:
        jobs: list[JobCreate] = []
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            for board in self.boards:
                try:
                    response = await client.get(
                        f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs",
                        params={"content": "true"},
                    )
                    response.raise_for_status()
                    for item in response.json().get("jobs", []):
                        title = str(item.get("title", ""))
                        description = html.unescape(str(item.get("content", "")))
                        text = f"{title} {description}".lower()
                        if keywords and not any(word.lower() in text for word in keywords):
                            continue
                        location = str((item.get("location") or {}).get("name", ""))
                        jobs.append(JobCreate(
                            source="greenhouse",
                            source_job_id=str(item["id"]),
                            canonical_url=str(item["absolute_url"]),
                            title=title,
                            employer=board,
                            location=location,
                            description=description,
                            remote="remote" in location.lower(),
                            work_arrangement="remote" if "remote" in location.lower() else "",
                        ))
                except (httpx.HTTPError, ValueError, KeyError):
                    continue
        return jobs
