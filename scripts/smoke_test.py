"""Verify database, API import, and dashboard import."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import init_db
from app.api.main import app


def main() -> None:
    init_db()
    assert app.title
    from app.dashboard import app as dashboard_module
    print("Smoke test passed: database and application modules loaded.")


if __name__ == "__main__":
    main()
