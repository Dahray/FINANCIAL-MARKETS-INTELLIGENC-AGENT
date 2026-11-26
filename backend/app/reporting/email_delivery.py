"""
Gmail / SMTP TLS Executive Intelligence Report Delivery Service (Section 2 & Section 9).
Delivers HTML executive briefs with the 5 Core Strategic Questions and attaches the
16-section PDF report and 8-sheet Excel data workbook.
"""

from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path
import smtplib
from typing import Any, Dict, List, Optional, Sequence

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("fmip.reporting.email")


class GmailDeliveryService:
    """Delivers weekly financial intelligence reports via Gmail SMTP/TLS."""

    @staticmethod
    def is_configured() -> bool:
        return bool(
            settings.EMAIL_DELIVERY_ENABLED
            and settings.SMTP_USERNAME
            and settings.SMTP_APP_PASSWORD
            and "CHANGE_ME" not in settings.SMTP_APP_PASSWORD
        )

    @staticmethod
    def build_executive_email_html(report_data: Dict[str, Any]) -> str:
        """Render institutional HTML executive brief email body."""
        code = report_data.get("report_code", "FMIP-WK")
        title = report_data.get("title", "Weekly Financial Markets Intelligence Report")
        exec_sum = report_data.get("executive_summary", "")
        five_q = report_data.get("five_strategic_questions", {})
        actions_html = "".join(
            f"<li style='margin-bottom:6px;'>{act}</li>"
            for act in five_q.get(
                "q5_what_strategic_actions_should_organisation_consider", []
            )
        )

        return f"""
<!DOCTYPE html>
<html>
<body style="font-family: 'Segoe UI', Arial, sans-serif; color: #0f172a; line-height: 1.6; max-width: 780px; margin: 0 auto; padding: 20px;">
  <div style="background-color: #0f172a; color: #ffffff; padding: 20px 24px; border-radius: 8px 8px 0 0;">
    <div style="font-size: 11px; color: #10b981; font-weight: bold; letter-spacing: 1px;">
      SOHCAHTOA HOLDINGS LIMITED • INSTITUTIONAL FINANCIAL RESEARCH DESK
    </div>
    <h2 style="margin: 6px 0 4px 0; font-size: 18px;">{title}</h2>
    <div style="font-size: 12px; color: #94a3b8;">Report Code: {code} • Verified by Chief Research Editor (Agent 8)</div>
  </div>

  <div style="border: 1px solid #cbd5e1; border-top: none; padding: 24px; border-radius: 0 0 8px 8px;">
    <h3 style="color: #064e3b; margin-top: 0;">1. Executive Summary</h3>
    <p style="font-size: 13.5px; color: #1e293b;">{exec_sum}</p>

    <h3 style="color: #064e3b;">2. The Five Core Strategic Questions</h3>
    <p style="font-size: 13px;"><strong>Q1. Where is the financial market currently?</strong><br/>{five_q.get('q1_where_is_market_currently', '')}</p>
    <p style="font-size: 13px;"><strong>Q2. What is changing in the market?</strong><br/>{five_q.get('q2_what_is_changing_in_market', '')}</p>
    <p style="font-size: 13px;"><strong>Q3. Where are the emerging opportunities?</strong><br/>{five_q.get('q3_where_are_emerging_opportunities', '')}</p>
    <p style="font-size: 13px;"><strong>Q4. What are the risks and threats?</strong><br/>{five_q.get('q4_what_are_risks_and_threats', '')}</p>
    <div style="background-color: #f0fdf4; border-left: 4px solid #10b981; padding: 12px 16px; margin-top: 12px;">
      <strong style="font-size: 13px; color: #065f46;">Q5. Strategic Actions for Management Consideration:</strong>
      <ul style="font-size: 13px; margin: 8px 0 0 0; padding-left: 20px;">{actions_html}</ul>
    </div>

    <p style="font-size: 12px; color: #64748b; margin-top: 20px; border-top: 1px solid #e2e8f0; padding-top: 12px;">
      Attached: (1) Complete 16-Section Institutional PDF Report ({code}.pdf) and (2) 8-Sheet Underlying Financial Data Workbook ({code}.xlsx).
    </p>
  </div>
</body>
</html>
""".strip()

    @classmethod
    def send_weekly_report_email(
        cls,
        report_data: Dict[str, Any],
        pdf_path: Optional[str | Path] = None,
        excel_path: Optional[str | Path] = None,
        recipients: Optional[Sequence[str]] = None,
    ) -> str:
        """
        Send the executive HTML brief with PDF & Excel attachments via Gmail SMTP/TLS.
        Returns delivery status: `'SENT'`, `'SKIPPED_NO_CREDENTIALS'`, or `'FAILED:<reason>'`.
        """
        target_recipients: List[str] = list(recipients or settings.recipient_list)
        if not cls.is_configured() or not target_recipients:
            logger.info(
                "Email delivery skipped (awaiting EMAIL_DELIVERY_ENABLED=true and SMTP_USERNAME/SMTP_APP_PASSWORD in .env)."
            )
            return "SKIPPED_NO_CREDENTIALS"

        code = report_data.get("report_code", "FMIP-WK")
        msg = EmailMessage()
        msg["Subject"] = f"[{code}] SohCahToa Weekly Financial Markets & Strategic Intelligence Report"
        msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>"
        msg["To"] = ", ".join(target_recipients)

        msg.set_content(str(report_data.get("executive_summary", "")))
        html_body = cls.build_executive_email_html(report_data)
        msg.add_alternative(html_body, subtype="html")

        if pdf_path and Path(pdf_path).exists():
            p_file = Path(pdf_path)
            msg.add_attachment(
                p_file.read_bytes(),
                maintype="application",
                subtype="pdf",
                filename=p_file.name,
            )

        if excel_path and Path(excel_path).exists():
            x_file = Path(excel_path)
            msg.add_attachment(
                x_file.read_bytes(),
                maintype="application",
                subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename=x_file.name,
            )

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                server.login(settings.SMTP_USERNAME, settings.SMTP_APP_PASSWORD)
                server.send_message(msg)
            logger.info("Sent Weekly Report %s via Gmail SMTP to %s", code, target_recipients)
            return "SENT"
        except Exception as exc:
            logger.warning("Gmail SMTP delivery failed for %s: %s", code, exc)
            return f"FAILED:{exc}"
