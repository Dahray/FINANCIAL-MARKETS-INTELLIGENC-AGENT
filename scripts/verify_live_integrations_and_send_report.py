"""
Live API Credential Verification & End-to-End Friday Report Delivery Script.
1. Verifies all configured API keys in `.env` (Gemini, Tavily, FMP, Alpha Vantage, FRED).
2. Runs a live provider ingestion sweep into PostgreSQL / SQL database.
3. Executes the 8-Agent Friday Weekly Intelligence Report Pipeline.
4. Generates the 16-Section PDF Report and 8-Sheet Excel Data Workbook.
5. Delivers the Executive Brief + PDF + Excel attachments via Gmail SMTP to `Afolabi.azeez@sohcahtoaholdings.com`.
6. Attempts Google Drive archiving to folder `1cCL2koCp9Qvjaq95T2pZP3sRPpCU2c5K`.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from app.db.session import get_session_factory, init_database_schema
from app.services.ingestion_service import IngestionService
from app.services.report_service import ReportService
from app.services.seed_service import bootstrap_platform_data


def main() -> None:
    get_settings.cache_clear()
    s = get_settings()

    print("=" * 78)
    print("1. LIVE CREDENTIAL CONFIGURATION AUDIT (.env)")
    print("=" * 78)
    status_matrix = {
        "GEMINI_API_KEY": "CONFIGURED" if bool(s.GEMINI_API_KEY) else "MISSING",
        "TAVILY_API_KEY": "CONFIGURED" if bool(s.TAVILY_API_KEY) else "MISSING",
        "FMP_API_KEY": "CONFIGURED" if bool(s.FMP_API_KEY) else "MISSING",
        "ALPHA_VANTAGE_API_KEY": "CONFIGURED" if bool(s.ALPHA_VANTAGE_API_KEY) else "MISSING",
        "FRED_API_KEY": "CONFIGURED" if bool(s.FRED_API_KEY) else "MISSING",
        "GMAIL_SMTP_DELIVERY": (
            f"ENABLED ({s.SMTP_USERNAME} -> {s.WEEKLY_REPORT_RECIPIENTS})"
            if s.EMAIL_DELIVERY_ENABLED
            else "DISABLED"
        ),
        "GOOGLE_DRIVE_ARCHIVER": (
            f"ENABLED (Folder ID: {s.GOOGLE_DRIVE_REPORTS_FOLDER_ID} | SA: {s.GOOGLE_DRIVE_SERVICE_ACCOUNT_EMAIL})"
            if s.GOOGLE_DRIVE_ENABLED
            else "DISABLED"
        ),
    }
    for k, v in status_matrix.items():
        print(f"  - {k}: {v}")

    print("\n" + "=" * 78)
    print("2. INITIALIZING DATABASE & RUNNING LIVE PROVIDER INGESTION SWEEP")
    print("=" * 78)
    init_database_schema()
    session_factory = get_session_factory()
    with session_factory() as db:
        bootstrap_platform_data(db, run_live_network_fetch=False)
        live_ingest = IngestionService.run_live_ingestion_cycle(db)
        print(json.dumps(live_ingest, indent=2, default=str))

        print("\n" + "=" * 78)
        print("3. EXECUTING 8-AGENT FRIDAY REPORT PIPELINE + PDF/EXCEL + GMAIL + DRIVE")
        print("=" * 78)
        report_res = ReportService.execute_friday_report_pipeline(db)
        print(f"  - Report Code         : {report_res['report_code']}")
        print(f"  - 16-Section PDF File : {report_res['pdf_file_path']}")
        print(f"  - 8-Sheet Excel File  : {report_res['excel_file_path']}")
        print(f"  - Google Drive PDF ID : {report_res['google_drive_pdf_id'] or 'Pending gcloud ADC login'}")
        print(f"  - Gmail Delivery      : {report_res['email_delivery_status']}")
    print("=" * 78)


if __name__ == "__main__":
    main()
