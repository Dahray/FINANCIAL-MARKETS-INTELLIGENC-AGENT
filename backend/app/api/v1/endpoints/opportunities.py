"""Investment & Business Opportunity Radar Endpoints (Section 6 & Section 8 Page 4)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.radar_service import OpportunityRadarService

router = APIRouter(prefix="/opportunities", tags=["Opportunity Radar"])


@router.get("")
def list_opportunities(
    opportunity_class: Optional[str] = Query(
        default=None, description="INVESTMENT_OPPORTUNITY | STRATEGIC_BUSINESS_OPPORTUNITY"
    ),
    radar_category: Optional[str] = Query(default=None),
    target_business_line: Optional[str] = Query(default=None),
    min_score: float = Query(default=0.0, ge=0.0, le=100.0),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Retrieve ranked investment and strategic business opportunities with theses and 10-criterion matrices."""
    return OpportunityRadarService.list_opportunities(
        db=db,
        opportunity_class=opportunity_class,
        radar_category=radar_category,
        target_business_line=target_business_line,
        min_score=min_score,
    )
