"""
n8n Workflow Automation Webhook & Schedule Configuration Endpoints (Section 9).
Supports:
- Daily market monitoring & news collection trigger
- Regulatory announcement monitoring trigger
- High-conviction Opportunity Radar alert trigger
- Weekly Friday research execution, PDF/Excel generation, Drive archiving & Gmail delivery
- User-configurable reporting time, reporting frequency, and alert preferences
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import AlertPreference
from app.providers.nigerian.nigerian_providers import (
    CBNDataProvider,
    NigerianRegulatorsMonitorProvider,
)
from app.services.ingestion_service import IngestionService
from app.services.radar_service import OpportunityRadarService
from app.services.report_service import ReportService

router = APIRouter(prefix="/webhooks", tags=["n8n Automation & Scheduling Preferences"])


class AlertPreferenceUpdateSchema(BaseModel):
    report_day_of_week: str = Field(default="FRI")
    report_time_wat: str = Field(default="16:30")
    report_frequency: str = Field(default="WEEKLY")
    email_recipients: List[str] = Field(default_factory=list)
    enable_daily_macro_alerts: bool = True
    enable_regulatory_circular_alerts: bool = True
    enable_high_conviction_opportunity_alerts: bool = True
    min_opportunity_score_threshold: float = Field(default=75.0, ge=0.0, le=100.0)


def _verify_n8n_secret(
    x_n8n_secret: Optional[str] = Header(default=None, alias="X-N8N-Webhook-Secret"),
) -> None:
    """Verify optional shared secret header when n8n invokes automation webhooks."""
    expected = settings.N8N_WEBHOOK_SHARED_SECRET
    if (
        expected
        and "CHANGE_ME" not in expected
        and x_n8n_secret is not None
        and x_n8n_secret != expected
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-N8N-Webhook-Secret header.",
        )


@router.post("/n8n/daily-market-ingestion")
def webhook_daily_market_and_news_ingestion(
    db: Session = Depends(get_db),
    _: None = Depends(_verify_n8n_secret),
) -> Dict[str, Any]:
    """n8n Workflow 1: Daily market monitoring & news collection."""
    summary = IngestionService.run_live_ingestion_cycle(db)
    return {
        "workflow": "01_daily_market_and_macro_ingestion",
        "status": "completed",
        "ingestion_summary": summary,
    }


@router.post("/n8n/regulatory-monitor")
def webhook_regulatory_announcement_monitor(
    db: Session = Depends(get_db),
    _: None = Depends(_verify_n8n_secret),
) -> Dict[str, Any]:
    """n8n Workflow 2: Regulatory announcement monitoring (CBN, SEC, PenCom, NAICOM, DMO)."""
    cbn = CBNDataProvider()
    reg = NigerianRegulatorsMonitorProvider()
    items = cbn.fetch_regulatory_publications() + reg.fetch_regulatory_publications()
    stats = IngestionService.ingest_research_items(db, items)
    return {
        "workflow": "02_regulatory_and_competitor_monitor",
        "status": "completed",
        "regulatory_ingestion": stats,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/n8n/opportunity-alerts")
def webhook_opportunity_radar_alerts(
    db: Session = Depends(get_db),
    _: None = Depends(_verify_n8n_secret),
) -> Dict[str, Any]:
    """n8n Workflow 3: Scan Opportunity Radar and return high-conviction alerts above threshold."""
    pref = db.execute(select(AlertPreference).limit(1)).scalar_one_or_none()
    threshold = float(pref.min_opportunity_score_threshold) if pref else 75.0
    high_conviction = OpportunityRadarService.list_opportunities(
        db=db, min_score=threshold
    )
    return {
        "workflow": "03_opportunity_radar_alerts",
        "status": "completed",
        "threshold_score": threshold,
        "qualifying_opportunities_count": len(high_conviction),
        "high_conviction_alerts": high_conviction,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/n8n/friday-weekly-report")
def webhook_friday_weekly_report_execution(
    db: Session = Depends(get_db),
    _: None = Depends(_verify_n8n_secret),
) -> Dict[str, Any]:
    """
    n8n Workflow 4: Execute Friday 8-Agent research cycle, generate 16-section PDF & 8-sheet Excel,
    archive to Google Drive, and deliver executive brief via Gmail.
    """
    result = ReportService.execute_friday_report_pipeline(db)
    return {
        "workflow": "04_friday_weekly_intelligence_report",
        "status": "completed",
        "report_code": result["report_code"],
        "pdf_file_path": result["pdf_file_path"],
        "excel_file_path": result["excel_file_path"],
        "google_drive_pdf_id": result["google_drive_pdf_id"],
        "google_drive_excel_id": result["google_drive_excel_id"],
        "email_delivery_status": result["email_delivery_status"],
        "published_at": result["published_at"],
    }


@router.get("/preferences")
def get_alert_preferences(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retrieve current reporting time, reporting frequency, and alert preferences."""
    pref = db.execute(select(AlertPreference).limit(1)).scalar_one_or_none()
    if not pref:
        pref = AlertPreference(
            report_day_of_week=settings.DEFAULT_REPORT_DAY_OF_WEEK,
            report_time_wat=settings.DEFAULT_REPORT_TIME_WAT,
            report_frequency="WEEKLY",
            email_recipients=settings.recipient_list,
            min_opportunity_score_threshold=75.0,
        )
        db.add(pref)
        db.commit()
        db.refresh(pref)

    return {
        "id": pref.id,
        "report_day_of_week": pref.report_day_of_week,
        "report_time_wat": pref.report_time_wat,
        "report_frequency": pref.report_frequency,
        "email_recipients": pref.email_recipients,
        "enable_daily_macro_alerts": pref.enable_daily_macro_alerts,
        "enable_regulatory_circular_alerts": pref.enable_regulatory_circular_alerts,
        "enable_high_conviction_opportunity_alerts": pref.enable_high_conviction_opportunity_alerts,
        "min_opportunity_score_threshold": float(pref.min_opportunity_score_threshold),
        "updated_at": pref.updated_at.isoformat(),
    }


@router.put("/preferences")
def update_alert_preferences(
    payload: AlertPreferenceUpdateSchema,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Update reporting time, reporting frequency, and alert preferences."""
    pref = db.execute(select(AlertPreference).limit(1)).scalar_one_or_none()
    if not pref:
        pref = AlertPreference()
        db.add(pref)

    pref.report_day_of_week = payload.report_day_of_week.upper()
    pref.report_time_wat = payload.report_time_wat
    pref.report_frequency = payload.report_frequency.upper()
    pref.email_recipients = payload.email_recipients or settings.recipient_list
    pref.enable_daily_macro_alerts = payload.enable_daily_macro_alerts
    pref.enable_regulatory_circular_alerts = payload.enable_regulatory_circular_alerts
    pref.enable_high_conviction_opportunity_alerts = (
        payload.enable_high_conviction_opportunity_alerts
    )
    pref.min_opportunity_score_threshold = payload.min_opportunity_score_threshold
    db.commit()
    db.refresh(pref)

    return {
        "status": "updated",
        "report_day_of_week": pref.report_day_of_week,
        "report_time_wat": pref.report_time_wat,
        "report_frequency": pref.report_frequency,
        "email_recipients": pref.email_recipients,
        "min_opportunity_score_threshold": float(pref.min_opportunity_score_threshold),
    }
