"""CLI script to initialize database schema and seed initial data + live provider ingestion."""

from __future__ import annotations

import json
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import get_session_factory, init_database_schema
from app.services.seed_service import bootstrap_platform_data


def main() -> None:
    init_database_schema()
    session_factory = get_session_factory()
    with session_factory() as db:
        summary = bootstrap_platform_data(db, run_live_network_fetch=True)
        print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
