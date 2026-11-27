"""
Phase 3 Automated Verification Suite:
Tests all 8 specialized AI agents, tool calling, the 11-Question research framework,
the 10-Criterion strategic business evaluation matrix, the 7-Dimension Opportunity Radar
with Evidence Quality Gate, Chief Research Editor source/numeric verification,
the 16-Section Weekly Report synthesis, and the Citation-Backed Executive AI Research Assistant.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_eight_agent_research_cycle_and_16_section_report() -> None:
    """Verify end-to-end 8-agent orchestration, Chief Editor audit, and 16-section report generation."""
    with TestClient(app) as client:
        resp = client.post("/api/v1/reports/generate")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # Verify report metadata & Friday-to-Friday period
        assert data["report_code"].startswith("FMIP-WK-")
        assert len(data["executive_summary"]) > 150

        # Verify all 5 Core Strategic Questions are answered
        five_q = data["five_strategic_questions"]
        for q_key in (
            "q1_where_is_market_currently",
            "q2_what_is_changing_in_market",
            "q3_where_are_emerging_opportunities",
            "q4_what_are_risks_and_threats",
            "q5_what_strategic_actions_should_organisation_consider",
        ):
            assert q_key in five_q and five_q[q_key]

        # Verify all 16 mandatory Weekly Report sections exist (plus v2.0 section_00 change-tracking diff)
        sections = data["sections"]
        assert len(sections) >= 16, f"Expected >= 16 sections, got {len(sections)}"
        expected_sections = [
            "section_01_executive_summary",
            "section_02_nigerian_financial_market_performance",
            "section_03_global_market_performance",
            "section_04_macroeconomic_developments",
            "section_05_fixed_income_market_analysis",
            "section_06_fx_market_analysis",
            "section_07_equity_market_analysis",
            "section_08_financial_services_industry_intelligence",
            "section_09_competitor_intelligence",
            "section_10_regulatory_developments",
            "section_11_investment_opportunity_radar",
            "section_12_strategic_business_opportunities",
            "section_13_risks_and_market_outlook",
            "section_14_next_week_economic_and_financial_calendar",
            "section_15_management_recommendations",
            "section_16_references_and_source_register",
        ]
        for sec_key in expected_sections:
            assert sec_key in sections, f"Missing report section: {sec_key}"

        # Verify Chief Research Editor (Agent 8) Quality Gate Audit
        ed = data["editorial_review"]
        assert ed["numeric_audit_passed"] is True
        assert ed["editor_verdict"] == "APPROVED_FOR_PUBLICATION"
        assert len(ed["contradictions_identified"]) >= 1
        assert len(ed["weak_assumptions_challenged"]) >= 1

        # Verify Section 16 Source Register contains traceable citations
        src_reg = sections["section_16_references_and_source_register"]["source_register"]
        assert len(src_reg) >= 4
        for src in src_reg:
            assert src["source_name"]
            assert src["url"]
            assert src["reliability_classification"]


def test_overview_11_question_developments_and_opportunity_radar() -> None:
    """Verify the 11-question development matrix, 7-dimension Opportunity Radar, and 10-criterion strategic matrix."""
    with TestClient(app) as client:
        r_ov = client.get("/api/v1/overview/dashboard")
        assert r_ov.status_code == 200
        ov = r_ov.json()

        devs = ov["latest_developments_11q"]
        assert len(devs) >= 2
        d0 = devs[0]
        # Verify all 11 mandatory questions are populated
        for q_col in (
            "q1_what_happened",
            "q2_why_it_happened",
            "q3_what_caused_it",
            "q4_why_significant",
            "q5_who_benefits",
            "q6_who_loses",
            "q7_immediate_implications",
            "q8_long_term_implications",
            "q9_opportunities_created",
            "q10_risks_introduced",
            "q11_management_considerations",
        ):
            assert d0[q_col], f"Missing 11-question field: {q_col}"
        # Verify epistemic separation (Facts, Estimates, Opinions, AI Interpretations)
        eb = d0["epistemic_breakdown"]
        assert len(eb["facts"]) >= 1
        assert len(eb["ai_interpretations"]) >= 1
        assert len(d0["source_register_ids"]) >= 1

        # Verify Opportunity Radar endpoint (Investment + Strategic Business Opportunities)
        r_opp = client.get("/api/v1/opportunities")
        assert r_opp.status_code == 200
        opps = r_opp.json()
        assert len(opps) >= 6

        strat_opps = [o for o in opps if o["opportunity_class"] == "STRATEGIC_BUSINESS_OPPORTUNITY"]
        assert len(strat_opps) >= 3
        s0 = strat_opps[0]["strategic_evaluation_matrix"]
        for crit in (
            "market_size",
            "market_growth",
            "customer_demand",
            "competitive_intensity",
            "revenue_potential",
            "profitability",
            "regulatory_requirements",
            "capital_requirements",
            "execution_difficulty",
            "strategic_fit",
        ):
            assert crit in s0 and s0[crit], f"Missing strategic evaluation criterion: {crit}"


def test_competitors_regulatory_and_executive_ai_assistant() -> None:
    """Verify Competitor Intelligence, Regulatory Monitor, and all 7 Executive Assistant benchmark questions."""
    with TestClient(app) as client:
        # 1. Competitor Profiles & Events
        r_cp = client.get("/api/v1/competitors/profiles")
        assert r_cp.status_code == 200
        assert len(r_cp.json()) >= 8

        r_ce = client.get("/api/v1/competitors/events")
        assert r_ce.status_code == 200
        assert len(r_ce.json()) >= 5
        assert r_ce.json()[0]["what_they_are_doing_differently"]
        assert r_ce.json()[0]["implications_for_our_business"]

        # 2. Regulatory Events & Source Register
        r_reg = client.get("/api/v1/regulatory/events")
        assert r_reg.status_code == 200
        assert len(r_reg.json()) >= 4
        assert r_reg.json()[0]["compliance_implications"]

        # 3. Test all 7 Benchmark Questions from Section 8 on the Citation-Backed AI Research Assistant
        benchmark_questions = [
            "What are the most attractive investment opportunities in Nigeria currently?",
            "What is happening in the Nigerian fixed-income market?",
            "Which asset management firms are gaining market share?",
            "What opportunities are emerging in the financial services industry?",
            "What has changed in the Nigerian FX market over the past three months?",
            "What are the biggest threats to the Nigerian financial market?",
            "Which sectors should we be paying attention to?",
        ]
        for question in benchmark_questions:
            r_ask = client.post("/api/v1/assistant/ask", json={"question": question})
            assert r_ask.status_code == 200, r_ask.text
            ans = r_ask.json()
            assert len(ans["answer_markdown"]) > 150
            assert "[Citation:" in ans["answer_markdown"] or len(ans["citations"]) >= 1
            assert len(ans["citations"]) >= 3


if __name__ == "__main__":
    tests = [
        test_eight_agent_research_cycle_and_16_section_report,
        test_overview_11_question_developments_and_opportunity_radar,
        test_competitors_regulatory_and_executive_ai_assistant,
    ]
    for fn in tests:
        fn()
        print(f"[PASS] {fn.__name__}")
    print(f"\nALL {len(tests)} PHASE 3 MULTI-AGENT TEST SUITES PASSED SUCCESSFULLY!")
