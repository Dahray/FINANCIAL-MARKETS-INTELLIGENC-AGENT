"""Competitive Intelligence Endpoints (Section 3 Agent 4 & Section 8 Page 5)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.intelligence import CompetitorEvent, CompetitorProfile
from app.services.radar_service import OpportunityRadarService

router = APIRouter(prefix="/competitors", tags=["Competitive Intelligence"])


@router.get("/profiles")
def list_competitor_profiles(
    category: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List tracked Nigerian and African financial services competitors across all 9 categories."""
    stmt = select(CompetitorProfile).order_by(CompetitorProfile.name.asc())
    if category:
        stmt = stmt.where(CompetitorProfile.category == category.upper())
    rows = db.execute(stmt).scalars().all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "category": r.category,
            "tier": r.tier,
            "headquarters": r.headquarters,
            "key_products": r.key_products,
            "aum_or_capital_estimate": r.aum_or_capital_estimate,
            "competitive_strengths": r.competitive_strengths,
            "vulnerabilities": r.vulnerabilities,
            "updated_at": r.updated_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/events")
def list_competitor_events(
    event_type: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List competitive intelligence developments, differentiation analysis, and counter-strategies."""
    OpportunityRadarService.ensure_radar_populated(db)
    stmt = select(CompetitorEvent).order_by(CompetitorEvent.event_date.desc())
    if event_type:
        stmt = stmt.where(CompetitorEvent.event_type == event_type.upper())
    rows = db.execute(stmt).scalars().all()
    comp_map = {
        c.id: c for c in db.execute(select(CompetitorProfile)).scalars().all()
    }
    return [
        {
            "id": r.id,
            "competitor_id": r.competitor_id,
            "competitor_name": comp_map[r.competitor_id].name if r.competitor_id in comp_map else "Institution",
            "competitor_category": comp_map[r.competitor_id].category if r.competitor_id in comp_map else "FINANCIAL_SERVICES",
            "event_type": r.event_type,
            "event_date": r.event_date.strftime("%Y-%m-%d"),
            "title": r.title,
            "summary": r.summary,
            "what_they_are_doing_differently": r.what_they_are_doing_differently,
            "implications_for_our_business": r.implications_for_our_business,
            "recommended_counter_strategy": r.recommended_counter_strategy,
            "threat_level": r.threat_level,
            "source_register_id": r.source_register_id,
        }
        for r in rows
    ]
