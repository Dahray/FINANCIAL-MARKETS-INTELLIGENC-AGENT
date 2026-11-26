"""
Redis-Backed Background Worker & Scheduled Job Runner (Section 2 & Section 9).
Processes queued ingestion, Opportunity Radar scans, and Friday Weekly Report generation tasks.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import get_session_factory, init_database_schema
from app.services.ingestion_service import IngestionService
from app.services.radar_service import OpportunityRadarService
from app.services.report_service import ReportService

logger = get_logger("fmip.workers.runner")

REDIS_JOB_QUEUE_KEY = "fmip:jobs:queue"


def process_single_job(job_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a background job (`DAILY_INGESTION`, `OPPORTUNITY_SCAN`, or `FRIDAY_WEEKLY_REPORT`)."""
    job_type = str(job_payload.get("job_type", "FRIDAY_WEEKLY_REPORT")).upper()
    init_database_schema()
    session_factory = get_session_factory()

    with session_factory() as db:
        if job_type == "DAILY_INGESTION":
            res = IngestionService.run_live_ingestion_cycle(db)
            return {"job_type": job_type, "status": "completed", "result": res}
        if job_type == "OPPORTUNITY_SCAN":
            opps = OpportunityRadarService.list_opportunities(db, min_score=75.0)
            return {
                "job_type": job_type,
                "status": "completed",
                "high_conviction_count": len(opps),
            }
        # Default: Full Friday Weekly Intelligence Report pipeline
        rpt = ReportService.execute_friday_report_pipeline(db)
        return {
            "job_type": "FRIDAY_WEEKLY_REPORT",
            "status": "completed",
            "report_code": rpt["report_code"],
            "pdf_file_path": rpt["pdf_file_path"],
            "excel_file_path": rpt["excel_file_path"],
        }


def run_worker_loop(max_iterations: Optional[int] = None) -> None:
    """Poll Redis job queue and execute background tasks."""
    logger.info("FMIP Redis Background Worker started.")
    redis_client = None
    try:
        import redis

        client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()
        redis_client = client
        logger.info("Connected to Redis queue at %s", settings.REDIS_URL)
    except Exception as exc:
        logger.info("Redis queue offline (%s); running standalone scheduled worker check.", exc)

    iterations = 0
    while True:
        iterations += 1
        if redis_client is not None:
            try:
                raw = redis_client.lpop(REDIS_JOB_QUEUE_KEY)
                if raw:
                    job = json.loads(str(raw))
                    process_single_job(job)
            except Exception as exc:
                logger.warning("Worker job processing error: %s", exc)

        if max_iterations is not None and iterations >= max_iterations:
            break
        time.sleep(5)


if __name__ == "__main__":
    run_worker_loop()
