from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


db_path = settings.database_url.replace("sqlite:///./", "")
if db_path.startswith("./"):
    db_path = db_path[2:]
if db_path and "/" in db_path:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def ensure_sqlite_schema() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    with engine.begin() as connection:
        result = connection.exec_driver_sql("PRAGMA table_info(jobs)").fetchall()
        existing = {row[1] for row in result}
        additions = {
            "work_arrangement": "VARCHAR(30) NOT NULL DEFAULT ''",
            "employment_type": "VARCHAR(100) NOT NULL DEFAULT ''",
            "experience_requirements": "TEXT NOT NULL DEFAULT ''",
            "required_qualifications": "TEXT NOT NULL DEFAULT ''",
            "preferred_qualifications": "TEXT NOT NULL DEFAULT ''",
            "last_verified_at": "DATETIME",
            "last_updated_at": "DATETIME",
            "status": "VARCHAR(30) NOT NULL DEFAULT 'active'",
        }
        for name, definition in additions.items():
            if name not in existing:
                connection.exec_driver_sql(f"ALTER TABLE jobs ADD COLUMN {name} {definition}")
