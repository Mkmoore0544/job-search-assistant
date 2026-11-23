from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.providers.base import JobProvider
from app.schemas import JobCreate


class USAJobsProvider(JobProvider):
    name = "usajobs"

    async def search(self, keywords: list[str], locations: list[str]) -> list[JobCreate]:
        if not settings.usajobs_api_key:
            return []
        headers = {
            "Authorization-Key": settings.usajobs_api_key,
            "User-Agent": settings.usajobs_user_agent or "job-search-assistant",
        }
        params: dict[str, str] = {"Keyword": " ".join(keywords)}
        if locations:
            params["LocationName"] = ";".join(locations)
        jobs: list[JobCreate] = []
        async with httpx.AsyncClient(timeout=20, headers=headers) as client:
            try:
                response = await client.get("https://data.usajobs.gov/api/search", params=params)
                response.raise_for_status()
                for item in response.json().get("SearchResult", {}).get("SearchResultItems", []):
                    position = item["MatchedObjectDescriptor"]
                    remuneration = position.get("PositionRemuneration") or []
                    salary_min = salary_max = None
                    if remuneration:
                        try:
                            salary_min = int(float(remuneration[0].get("MinimumRange") or 0)) or None
                            salary_max = int(float(remuneration[0].get("MaximumRange") or 0)) or None
                        except (TypeError, ValueError):
                            pass
                    location = ", ".join(
                        loc.get("LocationName", "") for loc in position.get("PositionLocation", [])
                    )
                    posted = position.get("PublicationStartDate")
                    jobs.append(JobCreate(
                        source="usajobs",
                        source_job_id=str(position["PositionID"]),
                        canonical_url=str(position["PositionURI"]),
                        title=str(position["PositionTitle"]),
                        employer=str(position["OrganizationName"]),
                        location=location,
                        description=str(position.get("UserArea", {}).get("Details", {}).get("JobSummary", "")),
                        salary_min=salary_min,
                        salary_max=salary_max,
                        remote="remote" in location.lower(),
                        work_arrangement="remote" if "remote" in location.lower() else "",
                        posted_at=posted,
                    ))
            except (httpx.HTTPError, ValueError, KeyError):
                return []
        return jobs
