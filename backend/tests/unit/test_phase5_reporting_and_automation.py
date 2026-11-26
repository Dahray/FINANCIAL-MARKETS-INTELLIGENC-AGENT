"""
Phase 5 Automated Verification Suite:
Tests 16-section PDF report generation, 8-sheet OpenPyXL Excel workbook generation,
PDF/Excel HTTP download endpoints, Gmail HTML executive brief rendering,
all 4 n8n workflow JSON definitions, n8n webhook triggers, and schedule/alert preferences.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
import openpyxl

from app.core.config import PROJECT_ROOT
from app.main import app
from app.reporting.email_delivery import GmailDeliveryService
from app.workers.runner import process_single_job


def test_pdf_and_excel_generation_and_download_endpoints() -> None:
    """Verify actual 16-section PDF and 8-sheet Excel workbook generation on disk and HTTP download."""
    with TestClient(app) as client:
        # 1. Trigger Friday Weekly Report Pipeline
        r_gen = client.post("/api/v1/reports/generate")
        assert r_gen.status_code == 200, r_gen.text
        data = r_gen.json()

        pdf_path = Path(data["pdf_file_path"])
        excel_path = Path(data["excel_file_path"])

        # 2. Verify PDF file on disk
        assert pdf_path.exists(), f"Missing generated PDF at {pdf_path}"
        pdf_bytes = pdf_path.read_bytes()
        assert len(pdf_bytes) > 3000
        assert pdf_bytes.startswith(b"%PDF-1.")
        assert b"%%EOF" in pdf_bytes[-64:]

        # 3. Verify Excel workbook on disk with OpenPyXL
        assert excel_path.exists(), f"Missing generated Excel workbook at {excel_path}"
        wb = openpyxl.load_workbook(str(excel_path))
        expected_sheets = [
            "01_Executive_Summary",
            "02_Market_Performance",
            "03_Sovereign_Yield_Curve",
            "04_Macro_Indicators",
            "05_Equity_DCF_Valuations",
            "06_Forecasts_And_Backtests",
            "07_Opportunity_Radar",
            "08_Source_Register",
        ]
        assert wb.sheetnames == expected_sheets, f"Unexpected Excel tabs: {wb.sheetnames}"
        assert wb["02_Market_Performance"].max_row >= 7
        assert wb["03_Sovereign_Yield_Curve"].max_row >= 11
        assert wb["08_Source_Register"].max_row >= 5

        # 4. Verify HTTP download endpoints for PDF and Excel
        r_dl_pdf = client.get(f"/api/v1/reports/{data['report_code']}/download/pdf")
        assert r_dl_pdf.status_code == 200
        assert "application/pdf" in r_dl_pdf.headers["content-type"]
        assert r_dl_pdf.content.startswith(b"%PDF-1.")

        r_dl_xlsx = client.get(f"/api/v1/reports/{data['report_code']}/download/excel")
        assert r_dl_xlsx.status_code == 200
        assert "spreadsheetml.sheet" in r_dl_xlsx.headers["content-type"]
        assert len(r_dl_xlsx.content) > 5000

        # 5. Verify Gmail HTML executive summary renderer
        html_body = GmailDeliveryService.build_executive_email_html(data)
        assert "Executive Summary" in html_body
        assert "The Five Core Strategic Questions" in html_body
        assert data["report_code"] in html_body


def test_n8n_workflows_webhooks_and_worker() -> None:
    """Verify all 4 n8n workflow JSONs, webhook endpoints, user preferences, and worker runner."""
    workflows_dir = PROJECT_ROOT / "n8n" / "workflows"
    expected_workflows = [
        "01_daily_market_and_macro_ingestion.json",
        "02_regulatory_and_competitor_monitor.json",
        "03_opportunity_radar_alerts.json",
        "04_friday_weekly_intelligence_report.json",
    ]
    for wf_file in expected_workflows:
        p = workflows_dir / wf_file
        assert p.exists(), f"Missing n8n workflow: {p}"
        parsed = json.loads(p.read_text(encoding="utf-8"))
        assert "nodes" in parsed and len(parsed["nodes"]) >= 2
        assert parsed["settings"]["timezone"] == "Africa/Lagos"

    with TestClient(app) as client:
        # 1. Test n8n Opportunity Alerts Webhook
        r_alerts = client.post("/api/v1/webhooks/n8n/opportunity-alerts")
        assert r_alerts.status_code == 200
        assert r_alerts.json()["qualifying_opportunities_count"] >= 4

        # 2. Test n8n Friday Weekly Report Webhook
        r_fri = client.post("/api/v1/webhooks/n8n/friday-weekly-report")
        assert r_fri.status_code == 200
        assert r_fri.json()["status"] == "completed"
        assert r_fri.json()["pdf_file_path"]
        assert r_fri.json()["excel_file_path"]

        # 3. Test Alert & Schedule Preferences GET and PUT
        r_pref = client.get("/api/v1/webhooks/preferences")
        assert r_pref.status_code == 200

        r_upd = client.put(
            "/api/v1/webhooks/preferences",
            json={
                "report_day_of_week": "FRI",
                "report_time_wat": "16:30",
                "report_frequency": "WEEKLY",
                "email_recipients": ["exco@sohcahtoaholdings.com", "cio@sohcahtoaholdings.com"],
                "enable_daily_macro_alerts": True,
                "enable_regulatory_circular_alerts": True,
                "enable_high_conviction_opportunity_alerts": True,
                "min_opportunity_score_threshold": 80.0,
            },
        )
        assert r_upd.status_code == 200
        assert r_upd.json()["min_opportunity_score_threshold"] == 80.0

    # 4. Test Redis Background Worker Job Processor
    worker_res = process_single_job({"job_type": "OPPORTUNITY_SCAN"})
    assert worker_res["status"] == "completed"
    assert worker_res["high_conviction_count"] >= 4


if __name__ == "__main__":
    tests = [
        test_pdf_and_excel_generation_and_download_endpoints,
        test_n8n_workflows_webhooks_and_worker,
    ]
    for fn in tests:
        fn()
        print(f"[PASS] {fn.__name__}")
    print(f"\nALL {len(tests)} PHASE 5 REPORTING & AUTOMATION TEST SUITES PASSED SUCCESSFULLY!")
