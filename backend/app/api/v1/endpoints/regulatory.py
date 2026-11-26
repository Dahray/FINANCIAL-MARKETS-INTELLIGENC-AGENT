"""Regulatory Monitor & Source Register Endpoints (Section 3 Agent 5, Section 5 & Section 8 Page 6)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.intelligence import RegulatoryEvent
from app.models.source import SourceRegister
from app.services.radar_service import OpportunityRadarService

router = APIRouter(prefix="/regulatory", tags=["Regulatory Monitor & Source Register"])


@router.get("/events")
def list_regulatory_events(
    regulator_code: Optional[str] = Query(
        default=None, description="CBN | SEC_NG | NGX | PENCOM | NAICOM | FRC_NG | FMF_NG"
    ),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Retrieve official regulatory circulars, compliance implications, and business opportunities."""
    OpportunityRadarService.ensure_radar_populated(db)
    stmt = select(RegulatoryEvent).order_by(RegulatoryEvent.issued_date.desc())
    if regulator_code:
        stmt = stmt.where(RegulatoryEvent.regulator_code == regulator_code.upper())
    rows = db.execute(stmt).scalars().all()
    return [
        {
            "id": r.id,
            "regulator_code": r.regulator_code,
            "regulator_name": r.regulator_name,
            "reference_number": r.reference_number,
            "title": r.title,
            "issued_date": r.issued_date.strftime("%Y-%m-%d"),
            "policy_summary": r.policy_summary,
            "compliance_implications": r.compliance_implications,
            "capital_or_operational_impact": r.capital_or_operational_impact,
            "business_opportunities_created": r.business_opportunities_created,
            "affected_segments": r.affected_segments,
            "severity": r.severity,
            "is_official_publication": r.is_official_publication,
            "source_register_id": r.source_register_id,
        }
        for r in rows
    ]


@router.get("/source-register")
def list_source_register(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Return the complete traceable Source Register with reliability and epistemic classifications."""
    rows = (
        db.execute(
            select(SourceRegister)
            .order_by(SourceRegister.publication_date.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": r.id,
            "source_id": r.source_id,
            "source_name": r.source_name,
            "publication_title": r.publication_title,
            "publication_date": r.publication_date.isoformat(),
            "retrieval_date": r.retrieval_date.isoformat(),
            "url": r.url,
            "relevant_finding": r.relevant_finding,
            "reliability_classification": r.reliability_classification,
            "epistemic_type": r.epistemic_type,
            "verification_status": r.verification_status,
        }
        for r in rows
    ]
