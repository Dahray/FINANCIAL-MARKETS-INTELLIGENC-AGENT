"""
End-to-End Friday Weekly Intelligence Reporting & Delivery Service (Section 7 & Phase 5).
Executes the 8-Agent research cycle, generates the 16-section PDF report and 8-sheet
Excel data workbook, archives to Google Drive, delivers via Gmail, and updates PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.graph import run_full_multi_agent_research_cycle
from app.models.report import WeeklyReport
from app.reporting.drive_archiver import GoogleDriveArchiver
from app.reporting.email_delivery import GmailDeliveryService
from app.reporting.excel_generator import generate_weekly_report_excel
from app.reporting.pdf_generator import generate_weekly_report_pdf


class ReportService:
    """Orchestrates weekly report synthesis, PDF/Excel file generation, cloud archiving, and email delivery."""

    @staticmethod
    def ensure_report_artifacts(
        db: Session,
        report: WeeklyReport,
        chart_series_payload: Optional[Dict[str, Any]] = None,
    ) -> WeeklyReport:
        """Ensure both PDF (with verified Matplotlib charts) and Excel files exist on disk."""
        if chart_series_payload is None:
            from app.services.institutional_research_analytics import InstitutionalMarketResearchAssembler

            chart_series_payload = InstitutionalMarketResearchAssembler._build_chart_series_payload(db)

        report_payload: Dict[str, Any] = {
            "report_code": report.report_code,
            "title": report.title,
            "period_start_friday": report.period_start_friday.isoformat(),
            "period_end_friday": report.period_end_friday.isoformat(),
            "executive_summary": report.executive_summary,
            "five_strategic_questions": report.five_strategic_questions_json,
            "sections": report.sections_json,
            "chart_series_payload": chart_series_payload,
        }

        pdf_path = generate_weekly_report_pdf(report_payload)
        excel_path = generate_weekly_report_excel(report_payload)

        report.pdf_file_path = str(pdf_path.resolve())
        report.excel_file_path = str(excel_path.resolve())

        # Optional Google Drive archiving
        drive_pdf_id = GoogleDriveArchiver.upload_file_to_drive(
            pdf_path, mime_type="application/pdf"
        )
        drive_excel_id = GoogleDriveArchiver.upload_file_to_drive(
            excel_path,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        if drive_pdf_id:
            report.google_drive_pdf_id = drive_pdf_id
        if drive_excel_id:
            report.google_drive_excel_id = drive_excel_id

        # Optional Gmail delivery
        delivery_status = GmailDeliveryService.send_weekly_report_email(
            report_data=report_payload,
            pdf_path=pdf_path,
            excel_path=excel_path,
        )
        report.email_delivery_status = delivery_status

        db.commit()
        db.refresh(report)
        return report

    @classmethod
    def execute_friday_report_pipeline(
        cls,
        db: Session,
        reference_dt: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Run the complete Friday Reporting Pipeline:
        1. Execute all 8 specialized agents via LangGraph (`run_full_multi_agent_research_cycle`).
        2. Generate the 16-section PDF report (`ReportLab` / PDF 1.4).
        3. Generate the 8-sheet Excel workbook (`OpenPyXL`).
        4. Archive to Google Drive (if enabled in `.env`).
        5. Deliver executive brief + attachments via Gmail (if enabled in `.env`).
        """
        weekly_report, state = run_full_multi_agent_research_cycle(
            db=db,
            run_type="WEEKLY_FRIDAY_REPORT",
            reference_dt=reference_dt,
        )
        weekly_report = cls.ensure_report_artifacts(db, weekly_report)

        return {
            "id": weekly_report.id,
            "report_code": weekly_report.report_code,
            "title": weekly_report.title,
            "period_start_friday": weekly_report.period_start_friday.isoformat(),
            "period_end_friday": weekly_report.period_end_friday.isoformat(),
            "executive_summary": weekly_report.executive_summary,
            "five_strategic_questions": weekly_report.five_strategic_questions_json,
            "sections": weekly_report.sections_json,
            "editorial_review": state.get("agent_8_editorial_review"),
            "pdf_file_path": weekly_report.pdf_file_path,
            "excel_file_path": weekly_report.excel_file_path,
            "google_drive_pdf_id": weekly_report.google_drive_pdf_id,
            "google_drive_excel_id": weekly_report.google_drive_excel_id,
            "email_delivery_status": weekly_report.email_delivery_status,
            "published_at": weekly_report.published_at.isoformat(),
        }

    @classmethod
    def get_or_create_report_file(
        cls,
        db: Session,
        report_code: str,
        file_format: str = "pdf",
    ) -> Path:
        """Return the Path to the generated PDF or Excel file for `report_code` (or `'latest'`)."""
        if report_code.lower() == "latest":
            rpt = (
                db.execute(
                    select(WeeklyReport).order_by(WeeklyReport.published_at.desc()).limit(1)
                )
                .scalar_one_or_none()
            )
            if rpt is None:
                rpt, _ = run_full_multi_agent_research_cycle(db)
        else:
            rpt = db.execute(
                select(WeeklyReport).where(WeeklyReport.report_code == report_code.upper())
            ).scalar_one_or_none()
            if rpt is None:
                rpt, _ = run_full_multi_agent_research_cycle(db)

        assert rpt is not None
        target_col = rpt.pdf_file_path if file_format == "pdf" else rpt.excel_file_path
        if not target_col or not Path(target_col).exists():
            rpt = cls.ensure_report_artifacts(db, rpt)
            target_col = rpt.pdf_file_path if file_format == "pdf" else rpt.excel_file_path

        assert target_col is not None
        return Path(target_col)
