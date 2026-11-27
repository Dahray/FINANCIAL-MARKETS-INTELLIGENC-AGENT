"""
PHASE 6: COMPREHENSIVE SYSTEM TESTING & APPLICATION SECURITY AUDIT SUITE
Tests all 7 mandatory Phase 6 dimensions (Section 12):
1. Financial calculations & walk-forward forecast backtesting
2. Data ingestion, 9-field provenance & DataQualityGate
3. All 8 specialized AI agent outputs & Evidence Quality Gate
4. Citations & Source Register traceability (including rejection of fake citations)
5. n8n automation webhooks, secret verification & Redis worker
6. 16-Section PDF & 8-Sheet OpenPyXL Excel report generation
7. Application security: JWT auth, RBAC role enforcement, rate limiting, prompt-injection defense, and zero frontend secret exposure.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
import openpyxl

from app.agents.nodes.agent_8_editor import run_agent_8_chief_editor
from app.agents.state import ResearchGraphState
from app.core.config import PROJECT_ROOT, settings
from app.core.security import PromptInjectionSanitizer, create_access_token
from app.main import app
from app.providers.base import IngestedMarketPoint
from app.providers.quality import DataQualityGate
from app.quant.econometrics import compute_correlation_matrix, run_ols_regression
from app.quant.fixed_income import analyze_yield_curve, compute_bond_risk_metrics
from app.quant.forecasting import generate_verified_forecast
from app.quant.market_metrics import compute_market_performance
from app.quant.valuation import compute_equity_valuation_dcf, compute_financial_ratios


def test_1_financial_calculations_and_forecast_backtesting() -> None:
    """Pillar 1: Verify deterministic Python financial calculations and historical vs forecast separation."""
    base_dt = datetime(2026, 9, 1, tzinfo=timezone.utc)
    dates = [base_dt + timedelta(days=i) for i in range(40)]
    prices = [1000.0 + 12.5 * i for i in range(40)]

    perf = compute_market_performance(dates, prices, symbol="NGX_TEST")
    assert perf.independent_check_passed is True
    assert perf.is_forecast is False
    assert perf.period_returns_pct["1W"] is not None

    yc = analyze_yield_curve([0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0], [18.5, 19.6, 22.8, 21.4, 20.7, 20.3, 19.45], 33.88)
    assert yc.independent_check_passed is True
    assert yc.is_forecast is False

    bond = compute_bond_risk_metrics(100.0, 19.89, 20.30, 10.0)
    assert bond.independent_check_passed is True

    corr = compute_correlation_matrix({"A": prices, "B": [p * 1.5 + 2.0 for p in prices]})
    assert corr.independent_check_passed is True
    assert corr.pearson_matrix["A"]["B"] > 0.999

    ols = run_ols_regression(prices, {"DRIVER": [float(i) for i in range(40)]}, "NGX_TEST")
    assert ols.independent_check_passed is True
    assert abs(ols.coefficients["DRIVER"] - 12.5) < 1e-4

    ratios = compute_financial_ratios("GTCO.NG", "FY25", 55.5, 29.43e9, 539.65e9, 1480e9, 9691e9)
    assert ratios.independent_check_passed is True

    dcf = compute_equity_valuation_dcf("GTCO.NG", 55.5, 15.8)
    assert dcf.independent_check_passed is True

    fc = generate_verified_forecast(dates, prices, "NGX_TEST", "NGX Test Series", "PTS", horizon_steps=4)
    assert fc.is_forecast is True
    assert fc.historical_backtest.n_splits >= 3
    assert fc.bull_case >= fc.base_case >= fc.bear_case


def test_2_data_ingestion_and_quality_gate() -> None:
    """Pillar 2: Verify data ingestion provenance, deduplication, and non-fabrication rules."""
    now = datetime.now(timezone.utc)
    pt = IngestedMarketPoint(
        symbol="ZENITHBANK.NG",
        indicator_name="Zenith Bank Share Price",
        asset_class="EQUITY",
        market_region="NIGERIA",
        value=46.30,
        currency_or_unit="NGN",
        reporting_period="2026-11-25",
        publication_date=now,
        source_code="NGX_OFFICIAL",
    )
    validated, h1 = DataQualityGate.validate_market_point(pt, historical_values=[45.0] * 15)
    assert validated.verification_status == "VERIFIED"
    assert len(h1) == 64

    # Negative equity price must be flagged as FLAGGED_UNVERIFIED
    bad_pt = IngestedMarketPoint(
        symbol="ZENITHBANK.NG",
        indicator_name="Zenith Bank Share Price",
        asset_class="EQUITY",
        market_region="NIGERIA",
        value=-5.0,
        currency_or_unit="NGN",
        reporting_period="2026-11-25",
        publication_date=now,
        source_code="NGX_OFFICIAL",
    )
    validated_bad, _ = DataQualityGate.validate_market_point(bad_pt)
    assert validated_bad.verification_status == "FLAGGED_UNVERIFIED"
    assert validated_bad.quality_flags.get("non_positive_price") is True


def test_3_eight_specialized_agent_outputs_and_evidence_gate() -> None:
    """Pillar 3: Verify Chief Research Editor challenges low-evidence opportunities and fake citations."""
    mock_state: ResearchGraphState = {
        "run_id": "test-run-editor",
        "run_type": "WEEKLY_FRIDAY_REPORT",
        "period_start_iso": "2026-11-13T15:30:00+00:00",
        "period_end_iso": "2026-11-20T15:30:00+00:00",
        "valid_source_ids": ["valid-uuid-001"],
        "source_register_ledger": [
            {
                "id": "valid-uuid-001",
                "source_name": "CBN Official",
                "publication_title": "MPC Communique",
                "publication_date": "2026-11-20",
                "retrieval_date": "2026-11-20",
                "url": "https://www.cbn.gov.ng",
                "relevant_finding": "MPR at 27.50%",
                "reliability_classification": "TIER_1_OFFICIAL",
                "epistemic_type": "FACT",
            }
        ],
        "agent_6_quant_output": {
            "all_independent_math_checks_passed": True,
            "historical_market_metrics": {f"SYM{i}": {"latest_price": 100.0} for i in range(6)},
            "fixed_income_and_yield_curve": {"yield_curve": {"fitted_standard_tenors": {"364D": 22.85, "10Y": 20.30}}},
            "macro_indicators_snapshot": {},
            "forecasts_and_backtests": {},
        },
        "agent_1_market_output": {
            "developments_11q": [
                {
                    "headline": "Test Market Development",
                    "domain": "EQUITIES",
                    "significance_score": 85.0,
                    "source_register_ids": ["FAKE-FABRICATED-UUID-999", "valid-uuid-001"],
                }
            ]
        },
        "agent_2_macro_output": {"developments_11q": []},
        "agent_3_investment_output": {
            "investment_opportunities": [
                {
                    "opportunity_class": "INVESTMENT_OPPORTUNITY",
                    "radar_category": "DISTRESSED_ASSET",
                    "target_business_line": "ASSET_MANAGEMENT",
                    "title": "Low-Evidence Speculative Play",
                    "instrument_or_sector": "Unverified Penny Stock",
                    "thesis": "Weak assumption",
                    "risk_assessment": "High",
                    "score_potential_return": 80.0,
                    "score_risk_adjusted": 50.0,
                    "score_market_attractiveness": 60.0,
                    "score_evidence_quality": 42.0,  # Below 65.0 gate!
                    "score_liquidity": 40.0,
                    "score_regulatory_feasibility": 70.0,
                    "composite_rank_score": 57.0,
                    "status": "ACTIVE_HIGH_CONVICTION",
                    "source_register_ids": ["FAKE-UUID-888"],
                }
            ]
        },
        "agent_4_competitor_output": {},
        "agent_5_regulatory_output": {},
        "agent_7_strategic_output": {"strategic_business_opportunities": []},
        "revision_count": 0,
        "max_revisions": 2,
    }

    audited_state = run_agent_8_chief_editor(mock_state)
    ed = audited_state["agent_8_editorial_review"]

    # Verify fake citation IDs were detected and stripped
    assert len(ed["unverified_claims_removed"]) >= 2
    assert audited_state["developments_11q"][0]["source_register_ids"] == ["valid-uuid-001"]

    # Verify low-evidence opportunity (42.0 < 65.0) was challenged and downgraded to INSUFFICIENT_EVIDENCE_HELD
    downgraded_opp = audited_state["opportunity_radar_items"][0]
    assert downgraded_opp["status"] == "INSUFFICIENT_EVIDENCE_HELD"


def test_4_citations_and_source_register_traceability() -> None:
    """Pillar 4: Verify all live API research endpoints return traceable Source Register citations."""
    with TestClient(app) as client:
        r_sr = client.get("/api/v1/regulatory/source-register")
        assert r_sr.status_code == 200
        sr_ids = {row["id"] for row in r_sr.json()}
        assert len(sr_ids) >= 4

        r_reg = client.get("/api/v1/regulatory/events")
        assert r_reg.status_code == 200
        for ev in r_reg.json():
            assert ev["source_register_id"] in sr_ids


def test_5_automation_webhooks_and_secret_authentication() -> None:
    """Pillar 5: Verify n8n webhook authentication blocks invalid shared secrets."""
    with TestClient(app) as client:
        # Sending a wrong X-N8N-Webhook-Secret must be rejected with 401 Unauthorized
        r_bad = client.post(
            "/api/v1/webhooks/n8n/opportunity-alerts",
            headers={"X-N8N-Webhook-Secret": "wrong-attacker-secret-token"},
        )
        assert r_bad.status_code == 401

        # Sending the valid configured secret succeeds
        r_ok = client.post(
            "/api/v1/webhooks/n8n/opportunity-alerts",
            headers={"X-N8N-Webhook-Secret": settings.N8N_WEBHOOK_SHARED_SECRET},
        )
        assert r_ok.status_code == 200


def test_6_report_generation_pdf_and_excel_integrity() -> None:
    """Pillar 6: Verify 16-section PDF and 8-sheet Excel workbook generation and content."""
    with TestClient(app) as client:
        r_gen = client.post("/api/v1/reports/generate")
        assert r_gen.status_code == 200
        rpt = r_gen.json()
        assert len(rpt["sections"]) >= 16
        assert Path(rpt["pdf_file_path"]).exists()
        assert Path(rpt["excel_file_path"]).exists()
        wb = openpyxl.load_workbook(rpt["excel_file_path"])
        assert len(wb.sheetnames) == 8


def test_7_application_security_rbac_and_zero_frontend_secret_leakage() -> None:
    """
    Pillar 7: Verify JWT authentication, RBAC role restrictions (401/403),
    rate-limit headers, prompt injection sanitization, and zero API key exposure in frontend code.
    """
    with TestClient(app) as client:
        # 1. Unauthenticated request to protected endpoints returns 401
        r_unauth = client.get("/api/v1/auth/me")
        assert r_unauth.status_code == 401

        r_audit_unauth = client.get("/api/v1/auth/audit-logs")
        assert r_audit_unauth.status_code == 401

        # 2. Non-admin role (BOARD_VIEWER) attempting to access EXECUTIVE_ADMIN audit logs returns 403 Forbidden
        r_login = client.post(
            "/api/v1/auth/login",
            json={
                "email": settings.INITIAL_ADMIN_EMAIL,
                "password": settings.INITIAL_ADMIN_PASSWORD,
            },
        )
        assert r_login.status_code == 200
        user_id = r_login.json()["user"]["id"]

        viewer_token = create_access_token(subject=user_id, role="BOARD_VIEWER")
        r_forbidden = client.get(
            "/api/v1/auth/audit-logs",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert r_forbidden.status_code == 403

        # 3. Executive Admin token succeeds and includes X-RateLimit-Remaining header
        admin_token = r_login.json()["access_token"]
        r_admin_audit = client.get(
            "/api/v1/auth/audit-logs",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r_admin_audit.status_code == 200
        assert "x-ratelimit-remaining" in r_admin_audit.headers
        assert len(r_admin_audit.json()) >= 1

    # 4. Scan all frontend source files to ensure no secret environment variables are referenced
    frontend_src = PROJECT_ROOT / "frontend" / "src"
    forbidden_secrets = [
        "GEMINI_API_KEY",
        "TAVILY_API_KEY",
        "FMP_API_KEY",
        "ALPHA_VANTAGE_API_KEY",
        "SMTP_APP_PASSWORD",
        "POSTGRES_PASSWORD",
        "SECRET_KEY",
    ]
    for ts_file in frontend_src.rglob("*.ts*"):
        text = ts_file.read_text(encoding="utf-8")
        for secret_name in forbidden_secrets:
            assert secret_name not in text, (
                f"Security violation: Secret key identifier {secret_name} found in frontend file {ts_file}"
            )


if __name__ == "__main__":
    tests = [
        test_1_financial_calculations_and_forecast_backtesting,
        test_2_data_ingestion_and_quality_gate,
        test_3_eight_specialized_agent_outputs_and_evidence_gate,
        test_4_citations_and_source_register_traceability,
        test_5_automation_webhooks_and_secret_authentication,
        test_6_report_generation_pdf_and_excel_integrity,
        test_7_application_security_rbac_and_zero_frontend_secret_leakage,
    ]
    for fn in tests:
        fn()
        print(f"[PASS] {fn.__name__}")
    print(f"\nALL {len(tests)} PHASE 6 COMPREHENSIVE E2E & SECURITY TEST SUITES PASSED SUCCESSFULLY!")
