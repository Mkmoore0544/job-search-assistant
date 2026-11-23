import asyncio
import threading
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from app.core.config import settings
from app.database import SessionLocal
from app.models import CompanyWatchlist, SearchPreference, SearchRun
from app.providers.greenhouse import GreenhouseProvider
from app.providers.lever import LeverProvider
from app.providers.usajobs import USAJobsProvider
from app.providers.adzuna import AdzunaProvider
from app.providers.remotive import RemotiveProvider
from app.providers.ashby import AshbyProvider
from app.services.jobs import persist_and_match

_lock = threading.Lock()
scheduler = BackgroundScheduler(timezone="UTC")


async def run_search_async() -> SearchRun:
    db = SessionLocal()
    run = SearchRun(status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    errors: list[str] = []
    discovered = 0
    new_count = 0
    try:
        preference = db.scalar(select(SearchPreference))
        keywords = [item.strip() for item in (preference.keywords if preference else "junior software developer").split(",") if item.strip()]
        locations = [item.strip() for item in (preference.locations if preference else "Remote, Texarkana TX").split(",") if item.strip()]
        enabled = {item.strip() for item in (preference.enabled_sources if preference else "greenhouse,lever").split(",") if item.strip()}
        providers = []
        if "greenhouse" in enabled:
            from app.core.config import settings
            boards = [item.strip() for item in settings.greenhouse_boards.split(",") if item.strip()]
            providers.append(GreenhouseProvider(boards))
        if "lever" in enabled:
            sites = [item.strip() for item in settings.lever_boards.split(",") if item.strip()]
            providers.append(LeverProvider(sites))
        if "usajobs" in enabled:
            providers.append(USAJobsProvider())
        if "adzuna" in enabled:
            providers.append(AdzunaProvider())
        if "remotive" in enabled:
            providers.append(RemotiveProvider())
        if "ashby" in enabled:
            boards = [item.strip() for item in settings.ashby_boards.split(",") if item.strip()]
            providers.append(AshbyProvider(boards))
        watchlist_rows = db.scalars(select(CompanyWatchlist).where(CompanyWatchlist.enabled.is_(True))).all()
        greenhouses = [row.ats_board for row in watchlist_rows if row.ats_type == "greenhouse" and row.ats_board]
        levers = [row.ats_board for row in watchlist_rows if row.ats_type == "lever" and row.ats_board]
        ashbys = [row.ats_board for row in watchlist_rows if row.ats_type == "ashby" and row.ats_board]
        if greenhouses:
            providers.append(GreenhouseProvider(greenhouses))
        if levers:
            providers.append(LeverProvider(levers))
        if ashbys:
            providers.append(AshbyProvider(ashbys))

        for provider in providers:
            try:
                listings = await provider.search(keywords, locations)
                discovered += len(listings)
                for listing in listings:
                    _, is_new = await persist_and_match(db, listing)
                    new_count += int(is_new)
            except Exception as exc:
                errors.append(f"{provider.name}: {type(exc).__name__}: {exc}")
        run.status = "completed" if not errors else "completed_with_errors"
    except Exception as exc:
        run.status = "failed"
        errors.append(f"search engine: {type(exc).__name__}: {exc}")
    finally:
        run.finished_at = datetime.now(timezone.utc)
        run.discovered = discovered
        run.new_jobs = new_count
        run.errors = "\n".join(errors)
        db.commit()
        db.refresh(run)
        db.close()
    return run


def run_search() -> None:
    if not _lock.acquire(blocking=False):
        return
    try:
        asyncio.run(run_search_async())
    finally:
        _lock.release()


def configure_scheduler() -> None:
    preference = None
    db = SessionLocal()
    try:
        preference = db.scalar(select(SearchPreference))
    finally:
        db.close()
    interval = preference.interval_hours if preference else settings.search_interval_hours
    if not scheduler.running:
        scheduler.add_job(run_search, "interval", hours=max(0.25, interval), id="job_search", replace_existing=True)
        scheduler.start()
    else:
        scheduler.reschedule_job("job_search", trigger="interval", hours=max(0.25, interval))
