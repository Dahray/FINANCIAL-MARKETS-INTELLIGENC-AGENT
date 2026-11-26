"""Executive Overview & Five Core Strategic Questions Endpoint (Section 8 Page 1)."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.graph import run_full_multi_agent_research_cycle
from app.agents.tools.research_tools import (
    tool_compute_all_market_metrics,
    tool_compute_yield_curve_and_bond_risk,
    tool_load_latest_macro_snapshot,
)
from app.db.session import get_db
from app.models.intelligence import MarketDevelopment
from app.models.opportunity import Opportunity
from app.models.report import EditorialReview, WeeklyReport

router = APIRouter(prefix="/overview", tags=["Executive Overview & 5 Core Questions"])


@router.get("/dashboard")
def get_executive_overview(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Consolidate the Executive Overview dashboard payload:
    - Market summary & major movements
    - 5 Core Strategic Questions (Final Objective)
    - Latest 11-question financial developments
    - Top ranked opportunities
    - Emerging risks & latest weekly report
    """
    latest_report = (
        db.execute(select(WeeklyReport).order_by(WeeklyReport.published_at.desc()).limit(1))
        .scalar_one_or_none()
    )
    if latest_report is None:
        latest_report, _ = run_full_multi_agent_research_cycle(db)

    market_metrics = tool_compute_all_market_metrics(db)
    fi_data = tool_compute_yield_curve_and_bond_risk(db)
    macro_snap = tool_load_latest_macro_snapshot(db)

    developments = (
        db.execute(
            select(MarketDevelopment)
            .order_by(MarketDevelopment.significance_score.desc())
            .limit(10)
        )
        .scalars()
        .all()
    )
    opportunities = (
        db.execute(
            select(Opportunity).order_by(Opportunity.composite_rank_score.desc()).limit(8)
        )
        .scalars()
        .all()
    )
    editorial = (
        db.execute(
            select(EditorialReview).order_by(EditorialReview.reviewed_at.desc()).limit(1)
        )
        .scalar_one_or_none()
    )

    return {
        "latest_report_summary": {
            "id": latest_report.id,
            "report_code": latest_report.report_code,
            "title": latest_report.title,
            "period_start_friday": latest_report.period_start_friday.isoformat(),
            "period_end_friday": latest_report.period_end_friday.isoformat(),
            "executive_summary": latest_report.executive_summary,
            "published_at": latest_report.published_at.isoformat(),
            "pdf_file_path": latest_report.pdf_file_path,
            "excel_file_path": latest_report.excel_file_path,
        },
        "five_strategic_questions": latest_report.five_strategic_questions_json,
        "market_metrics": market_metrics,
        "fixed_income_summary": fi_data,
        "macro_snapshot": macro_snap,
        "latest_developments_11q": [
            {
                "id": d.id,
                "headline": d.headline,
                "domain": d.domain,
                "market_region": d.market_region,
                "event_date": d.event_date.strftime("%Y-%m-%d"),
                "q1_what_happened": d.q1_what_happened,
                "q2_why_it_happened": d.q2_why_it_happened,
                "q3_what_caused_it": d.q3_what_caused_it,
                "q4_why_significant": d.q4_why_significant,
                "q5_who_benefits": d.q5_who_benefits,
                "q6_who_loses": d.q6_who_loses,
                "q7_immediate_implications": d.q7_immediate_implications,
                "q8_long_term_implications": d.q8_long_term_implications,
                "q9_opportunities_created": d.q9_opportunities_created,
                "q10_risks_introduced": d.q10_risks_introduced,
                "q11_management_considerations": d.q11_management_considerations,
                "quantitative_evidence": d.quantitative_evidence,
                "epistemic_breakdown": d.epistemic_breakdown,
                "significance_score": float(d.significance_score),
                "verification_status": d.verification_status,
                "source_register_ids": d.source_register_ids,
            }
            for d in developments
        ],
        "top_opportunities": [
            {
                "id": o.id,
                "opportunity_class": o.opportunity_class,
                "radar_category": o.radar_category,
                "target_business_line": o.target_business_line,
                "title": o.title,
                "instrument_or_sector": o.instrument_or_sector,
                "thesis": o.thesis,
                "risk_assessment": o.risk_assessment,
                "composite_rank_score": float(o.composite_rank_score),
                "score_evidence_quality": float(o.score_evidence_quality),
                "time_horizon": o.time_horizon,
                "status": o.status,
            }
            for o in opportunities
        ],
        "editorial_quality_gate": (
            {
                "verdict": editorial.editor_verdict,
                "numeric_audit_passed": editorial.numeric_audit_passed,
                "citation_audit_passed": editorial.citation_audit_passed,
                "contradictions_identified": editorial.contradictions_identified,
                "weak_assumptions_challenged": editorial.weak_assumptions_challenged,
            }
            if editorial
            else None
        ),
    }
