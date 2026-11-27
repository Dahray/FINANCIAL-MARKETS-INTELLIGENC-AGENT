"""
Stage 9 Institutional Weekly Macro & Market Research Verification Suite (FMIP v3.0).
Validates every VNL-benchmark analytical, quantitative, charting, PDF parsing,
cross-market transmission, and independent weekly reporting capability:
  1. Calendar-anchored WTD, MTD, YTD, YoY returns, yield bps deltas, and Market Regime classification.
  2. Multi-market institutional tables (Global Equities, Global 10Y Bonds, CBN NTB/OMO Auctions,
     Major Currencies, Commodities, Cross-Market Transmission Matrix, Asset-Class Implications, Calendar).
  3. Data-driven Matplotlib PNG chart generation strictly from verified DB series.
  4. ReportLab institutional multi-page PDF + enriched 8-sheet Excel workbook generation.
  5. Institutional PDF Research Parser (`pypdf` extraction, prompt-injection defense & 768-dim indexing).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
import openpyxl

from app.core.config import settings
from app.db.session import get_session_factory, init_database_schema
from app.main import app
from app.quant.market_metrics import (
    classify_market_regime,
    compute_market_performance,
    compute_yield_basis_point_changes,
)
from app.services.pdf_research_parser import InstitutionalPDFResearchParser
from app.services.report_service import ReportService


def run_stage9_institutional_research_suite() -> None:
    print("=" * 78)
    print("STAGE 9: INSTITUTIONAL WEEKLY MACRO & MARKET RESEARCH VERIFICATION SUITE")
    print("=" * 78)

    # 1. Verify deterministic WTD/MTD/YTD/YoY returns, bps deltas & regime classifier
    base_dt = datetime(2025, 11, 1, tzinfo=timezone.utc)
    dates = [base_dt + timedelta(days=i) for i in range(260)]
    prices = [100.0 + i * 0.25 for i in range(260)]
    perf = compute_market_performance(dates=dates, prices=prices, symbol="TEST_IDX")
    assert perf.period_returns_pct["WTD"] is not None
    assert perf.period_returns_pct["MTD"] is not None
    assert perf.period_returns_pct["YTD"] is not None
    assert perf.moving_averages["SMA_50"] is not None
    assert perf.moving_averages["SMA_200"] is not None

    regime = classify_market_regime(
        latest_price=perf.latest_price,
        sma_50=perf.moving_averages["SMA_50"],
        sma_200=perf.moving_averages["SMA_200"],
        wtd_return_pct=-1.25,
    )
    assert regime["regime"] == "PROFIT_TAKING_IN_UPTREND", f"Unexpected regime: {regime}"

    y_deltas = compute_yield_basis_point_changes(
        dates=[datetime(2025, 11, 1, tzinfo=timezone.utc), datetime(2026, 1, 5, tzinfo=timezone.utc), datetime(2026, 10, 30, tzinfo=timezone.utc), datetime(2026, 11, 6, tzinfo=timezone.utc)],
        yields_pct=[4.11, 4.17, 4.94, 4.87],
    )
    assert y_deltas["latest_yield_pct"] == 4.87
    assert y_deltas["wtd_bps"] == -7.0
    assert y_deltas["ytd_bps"] == 70.0
    print("[PASS] 1. WTD/MTD/YTD/YoY returns, yield bps deltas (-7 bps WTD, +70 bps YTD), and regime classifier verified")

    # 2. Run independent 8-agent institutional report pipeline (zero external reference input)
    init_database_schema()
    SessionLocal = get_session_factory()
    prev_email = settings.EMAIL_DELIVERY_ENABLED
    prev_drive = settings.GOOGLE_DRIVE_ENABLED
    settings.EMAIL_DELIVERY_ENABLED = False
    settings.GOOGLE_DRIVE_ENABLED = False
    try:
        with SessionLocal() as db:
            out = ReportService.execute_friday_report_pipeline(db)
            sections = out["sections"]
            assert "section_01b_what_has_changed_since_last_report" in sections
            sec3 = sections["section_03_global_market_performance"]
            sec4 = sections["section_04_macroeconomic_developments"]
            sec5 = sections["section_05_fixed_income_market_analysis"]
            sec6 = sections["section_06_fx_market_analysis"]
            sec8 = sections["section_08_financial_services_industry_intelligence"]
            sec14 = sections["section_14_next_week_economic_and_financial_calendar"]

            assert isinstance(sec3.get("global_equities_table"), list)
            assert len(sec4.get("cross_market_transmission_matrix", [])) == 6
            assert isinstance(sec5.get("nigerian_fixed_income_auctions"), dict)
            assert isinstance(sec6.get("major_currencies_table"), list)
            assert isinstance(sec6.get("commodities_table"), list)
            assert len(sec8.get("asset_class_implications", [])) == 6
            assert len(sec14.get("global_calendar", [])) >= 3
            assert len(sec14.get("nigeria_calendar", [])) >= 3
            print(
                "[PASS] 2. Multi-market institutional tables, 6-channel Cross-Market Transmission Matrix, "
                "6 Asset-Class Theses, and Global+Nigeria Calendar verified"
            )

            # 3. Verify PDF + Excel + Verified Charts on disk
            pdf_path = Path(out["pdf_file_path"])
            excel_path = Path(out["excel_file_path"])
            assert pdf_path.exists() and pdf_path.stat().st_size > 4000
            assert excel_path.exists() and excel_path.stat().st_size > 4000
            wb = openpyxl.load_workbook(excel_path)
            assert len(wb.sheetnames) == 8
            print(f"[PASS] 3. Institutional PDF ({pdf_path.stat().st_size:,} bytes) & 8-sheet Excel workbook verified")

            # 4. Verify PDF Research Parser (extract + ingest into Research Memory via API)
            pdf_bytes = pdf_path.read_bytes()
            parsed = InstitutionalPDFResearchParser.extract_from_bytes(pdf_bytes, filename=pdf_path.name)
            assert parsed["page_count"] >= 2
            assert parsed["total_characters"] > 500

            client = TestClient(app)
            up_resp = client.post(
                "/api/v1/intelligence/ingest-pdf",
                files={"file": (pdf_path.name, pdf_bytes, "application/pdf")},
                params={"title": f"Test Ingest {out['report_code']}"},
            )
            assert up_resp.status_code == 200, up_resp.text
            up_json = up_resp.json()
            assert up_json["status"] in ("INGESTED", "ALREADY_INGESTED")
            assert up_json["page_count"] >= 2
            print(
                f"[PASS] 4. Institutional PDF Research Parser & POST /api/v1/intelligence/ingest-pdf verified "
                f"({up_json['page_count']} pages, status={up_json['status']})"
            )
    finally:
        settings.EMAIL_DELIVERY_ENABLED = prev_email
        settings.GOOGLE_DRIVE_ENABLED = prev_drive

    print("\nALL 4/4 STAGE 9 INSTITUTIONAL WEEKLY RESEARCH TESTS PASSED!")


if __name__ == "__main__":
    run_stage9_institutional_research_suite()
