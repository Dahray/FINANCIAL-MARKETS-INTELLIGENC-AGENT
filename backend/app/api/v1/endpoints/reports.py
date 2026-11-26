"""Weekly Intelligence Reports, PDF/Excel File Downloads & Research Archive Endpoints (Section 7 & Section 8 Page 7)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.graph import run_full_multi_agent_research_cycle
from app.db.session import get_db
from app.models.document import ResearchDocument
from app.models.report import WeeklyReport
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Weekly Intelligence Reports & Archive"])


@router.get("")
def list_weekly_reports(
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List generated Friday-to-Friday Weekly Intelligence Reports."""
    rows = (
        db.execute(select(WeeklyReport).order_by(WeeklyReport.published_at.desc()))
        .scalars()
        .all()
    )
    if not rows:
        ReportService.execute_friday_report_pipeline(db)
        rows = (
            db.execute(select(WeeklyReport).order_by(WeeklyReport.published_at.desc()))
            .scalars()
            .all()
        )

    return [
        {
            "id": r.id,
            "report_code": r.report_code,
            "title": r.title,
            "period_start_friday": r.period_start_friday.isoformat(),
            "period_end_friday": r.period_end_friday.isoformat(),
            "executive_summary": r.executive_summary,
            "five_strategic_questions": r.five_strategic_questions_json,
            "sections_count": len(r.sections_json or {}),
            "pdf_file_path": r.pdf_file_path,
            "excel_file_path": r.excel_file_path,
            "google_drive_pdf_id": r.google_drive_pdf_id,
            "google_drive_excel_id": r.google_drive_excel_id,
            "email_delivery_status": r.email_delivery_status,
            "published_at": r.published_at.isoformat(),
        }
        for r in rows
    ]


@router.post("/generate")
def generate_weekly_report(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Execute the full 8-Agent research cycle, synthesize the 16-section Weekly Intelligence Report,
    generate the PDF report and 8-sheet Excel workbook, archive to Google Drive, and deliver via Gmail.
    """
    return ReportService.execute_friday_report_pipeline(db)


@router.get("/archive/search")
def search_research_archive(
    q: Optional[str] = Query(default=None, description="Keyword search across research archive"),
    document_type: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Search archived research documents, regulatory circulars, and financial statements."""
    stmt = select(ResearchDocument).order_by(ResearchDocument.published_at.desc())
    if document_type:
        stmt = stmt.where(ResearchDocument.document_type == document_type.upper())
    docs = db.execute(stmt.limit(100)).scalars().all()

    results = []
    q_low = q.lower().strip() if q else ""
    for d in docs:
        if q_low and (q_low not in d.title.lower() and q_low not in d.raw_text.lower()):
            continue
        results.append(
            {
                "id": d.id,
                "source_register_id": d.source_register_id,
                "document_type": d.document_type,
                "title": d.title,
                "issuer": d.issuer,
                "published_at": d.published_at.isoformat(),
                "retrieved_at": d.retrieved_at.isoformat(),
                "excerpt": d.raw_text[:450],
                "structured_extract": d.structured_extract,
            }
        )
    return results


@router.get("/{report_code}/download/pdf")
def download_weekly_report_pdf(
    report_code: str,
    db: Session = Depends(get_db),
) -> FileResponse:
    """Download the generated 16-section institutional PDF report."""
    pdf_path = ReportService.get_or_create_report_file(
        db=db, report_code=report_code, file_format="pdf"
    )
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=pdf_path.name,
    )


@router.get("/{report_code}/download/excel")
def download_weekly_report_excel(
    report_code: str,
    db: Session = Depends(get_db),
) -> FileResponse:
    """Download the generated 8-sheet OpenPyXL underlying data Excel workbook."""
    excel_path = ReportService.get_or_create_report_file(
        db=db, report_code=report_code, file_format="excel"
    )
    return FileResponse(
        path=str(excel_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=excel_path.name,
    )


@router.get("/{report_code}")
def get_weekly_report_detail(
    report_code: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve a specific 16-section Weekly Intelligence Report by `report_code` (or `'latest'`)."""
    if report_code.lower() == "latest":
        rpt = (
            db.execute(select(WeeklyReport).order_by(WeeklyReport.published_at.desc()).limit(1))
            .scalar_one_or_none()
        )
        if rpt is None:
            ReportService.execute_friday_report_pipeline(db)
            rpt = (
                db.execute(
                    select(WeeklyReport).order_by(WeeklyReport.published_at.desc()).limit(1)
                )
                .scalar_one_or_none()
            )
    else:
        rpt = db.execute(
            select(WeeklyReport).where(WeeklyReport.report_code == report_code.upper())
        ).scalar_one_or_none()

    if not rpt:
        raise HTTPException(status_code=404, detail=f"Weekly Report '{report_code}' not found.")

    if not rpt.pdf_file_path or not rpt.excel_file_path:
        rpt = ReportService.ensure_report_artifacts(db, rpt)

    return {
        "id": rpt.id,
        "report_code": rpt.report_code,
        "title": rpt.title,
        "period_start_friday": rpt.period_start_friday.isoformat(),
        "period_end_friday": rpt.period_end_friday.isoformat(),
        "executive_summary": rpt.executive_summary,
        "five_strategic_questions": rpt.five_strategic_questions_json,
        "sections": rpt.sections_json,
        "pdf_file_path": rpt.pdf_file_path,
        "excel_file_path": rpt.excel_file_path,
        "google_drive_pdf_id": rpt.google_drive_pdf_id,
        "google_drive_excel_id": rpt.google_drive_excel_id,
        "email_delivery_status": rpt.email_delivery_status,
        "published_at": rpt.published_at.isoformat(),
    }
