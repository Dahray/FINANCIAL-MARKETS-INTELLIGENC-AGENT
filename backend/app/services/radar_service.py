"""
Continuous Investment & Strategic Business Opportunity Radar Service (Section 6).
Scans, ranks, filters, and retrieves verified investment and business opportunities.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.graph import run_full_multi_agent_research_cycle
from app.models.opportunity import Opportunity


class OpportunityRadarService:
    """Manages the Investment & Business Opportunity Radar."""

    @staticmethod
    def ensure_radar_populated(db: Session) -> None:
        """If no opportunities have been persisted yet, trigger the 8-agent research cycle."""
        count = db.execute(select(Opportunity.id).limit(1)).scalar_one_or_none()
        if count is None:
            run_full_multi_agent_research_cycle(db, run_type="OPPORTUNITY_RADAR_SCAN")

    @classmethod
    def list_opportunities(
        cls,
        db: Session,
        opportunity_class: Optional[str] = None,
        radar_category: Optional[str] = None,
        target_business_line: Optional[str] = None,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """List ranked opportunities from the Opportunity Radar."""
        cls.ensure_radar_populated(db)
        stmt = select(Opportunity).order_by(Opportunity.composite_rank_score.desc())
        if opportunity_class:
            stmt = stmt.where(Opportunity.opportunity_class == opportunity_class.upper())
        if radar_category:
            stmt = stmt.where(Opportunity.radar_category == radar_category.upper())
        if target_business_line:
            stmt = stmt.where(Opportunity.target_business_line == target_business_line.upper())
        if min_score > 0:
            stmt = stmt.where(Opportunity.composite_rank_score >= min_score)

        rows = db.execute(stmt).scalars().all()
        return [
            {
                "id": r.id,
                "opportunity_class": r.opportunity_class,
                "radar_category": r.radar_category,
                "target_business_line": r.target_business_line,
                "title": r.title,
                "instrument_or_sector": r.instrument_or_sector,
                "geography": r.geography,
                "thesis": r.thesis,
                "supporting_quantitative_evidence": r.supporting_quantitative_evidence,
                "assumptions": r.assumptions,
                "risk_assessment": r.risk_assessment,
                "scores": {
                    "potential_return": float(r.score_potential_return),
                    "risk_adjusted": float(r.score_risk_adjusted),
                    "market_attractiveness": float(r.score_market_attractiveness),
                    "evidence_quality": float(r.score_evidence_quality),
                    "liquidity": float(r.score_liquidity),
                    "regulatory_feasibility": float(r.score_regulatory_feasibility),
                    "composite_rank_score": float(r.composite_rank_score),
                },
                "time_horizon": r.time_horizon,
                "strategic_evaluation_matrix": r.strategic_evaluation_matrix,
                "status": r.status,
                "source_register_ids": r.source_register_ids,
                "identified_at": r.identified_at.isoformat(),
            }
            for r in rows
        ]
