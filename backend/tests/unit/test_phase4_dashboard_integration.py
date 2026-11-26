"""
Phase 4 Automated Verification Suite:
Verifies all 8 mandatory Next.js institutional dashboard pages, authentication page,
financial visualization components, and end-to-end API contract compatibility with FastAPI.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import PROJECT_ROOT
from app.main import app


def test_all_8_mandatory_dashboard_pages_and_charts_exist() -> None:
    """Verify all required Next.js pages, charts, layout, and TypeScript modules exist and are populated."""
    frontend_dir = PROJECT_ROOT / "frontend"
    required_files = [
        "package.json",
        "tsconfig.json",
        "tailwind.config.ts",
        "src/types/intelligence.ts",
        "src/lib/api.ts",
        "src/components/ui/primitives.tsx",
        "src/components/charts/FinancialCharts.tsx",
        "src/components/layout/SidebarNav.tsx",
        "src/app/layout.tsx",
        "src/app/login/page.tsx",
        "src/app/(dashboard)/layout.tsx",
        "src/app/(dashboard)/overview/page.tsx",
        "src/app/(dashboard)/nigerian-markets/page.tsx",
        "src/app/(dashboard)/global-markets/page.tsx",
        "src/app/(dashboard)/opportunity-radar/page.tsx",
        "src/app/(dashboard)/competitive-intelligence/page.tsx",
        "src/app/(dashboard)/regulatory-monitor/page.tsx",
        "src/app/(dashboard)/research-reports/page.tsx",
        "src/app/(dashboard)/ai-assistant/page.tsx",
        "src/app/(dashboard)/settings/page.tsx",
    ]
    for rel_path in required_files:
        full_path = frontend_dir / rel_path
        assert full_path.exists(), f"Missing frontend file: {full_path}"
        content = full_path.read_text(encoding="utf-8")
        assert len(content) > 100, f"Frontend file appears empty or stubbed: {full_path}"


def test_frontend_to_backend_api_contracts() -> None:
    """Verify every API endpoint called by `fmipApi` in `frontend/src/lib/api.ts` returns matching JSON schemas."""
    with TestClient(app) as client:
        # Page 1: Overview
        r_ov = client.get("/api/v1/overview/dashboard")
        assert r_ov.status_code == 200
        ov = r_ov.json()
        assert "five_strategic_questions" in ov
        assert "latest_developments_11q" in ov
        assert "top_opportunities" in ov

        # Page 2: Nigerian Markets
        r_ngx = client.get("/api/v1/markets/timeseries?symbol=NGXASI&limit=40")
        assert r_ngx.status_code == 200
        assert len(r_ngx.json()) >= 30

        r_yc = client.get("/api/v1/markets/yield-curve?curve_name=NGN_SOVEREIGN_FMDQ")
        assert r_yc.status_code == 200
        assert "fitted_standard_tenors" in r_yc.json()["curve_analytics"]

        # Page 3: Global Markets & Econometrics
        r_econ = client.get("/api/v1/macro/econometrics")
        assert r_econ.status_code == 200
        assert "ols_regression_ngx_drivers" in r_econ.json()

        # Page 4: Opportunity Radar
        r_opp = client.get("/api/v1/opportunities")
        assert r_opp.status_code == 200
        assert len(r_opp.json()) >= 6

        # Page 5: Competitive Intelligence
        r_cp = client.get("/api/v1/competitors/profiles")
        assert r_cp.status_code == 200
        assert len(r_cp.json()) >= 8

        r_ce = client.get("/api/v1/competitors/events")
        assert r_ce.status_code == 200
        assert len(r_ce.json()) >= 5

        # Page 6: Regulatory Monitor & Source Register
        r_reg = client.get("/api/v1/regulatory/events")
        assert r_reg.status_code == 200
        assert len(r_reg.json()) >= 4

        r_sr = client.get("/api/v1/regulatory/source-register")
        assert r_sr.status_code == 200
        assert len(r_sr.json()) >= 4

        # Page 7: Research Reports & Searchable Archive
        r_rpt = client.get("/api/v1/reports/latest")
        assert r_rpt.status_code == 200
        assert len(r_rpt.json()["sections"]) == 16

        r_arch = client.get("/api/v1/reports/archive/search?q=CBN")
        assert r_arch.status_code == 200
        assert len(r_arch.json()) >= 1

        # Page 8: AI Research Assistant
        r_ai = client.post(
            "/api/v1/assistant/ask",
            json={"question": "What are the most attractive investment opportunities in Nigeria currently?"},
        )
        assert r_ai.status_code == 200
        assert "answer_markdown" in r_ai.json()
        assert "citations" in r_ai.json()


if __name__ == "__main__":
    tests = [
        test_all_8_mandatory_dashboard_pages_and_charts_exist,
        test_frontend_to_backend_api_contracts,
    ]
    for fn in tests:
        fn()
        print(f"[PASS] {fn.__name__}")
    print(f"\nALL {len(tests)} PHASE 4 FRONTEND DASHBOARD TEST SUITES PASSED SUCCESSFULLY!")
