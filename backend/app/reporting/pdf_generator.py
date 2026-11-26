"""
Institutional 16-Section Weekly Financial Markets Intelligence PDF Generator (Section 7).
Uses ReportLab Platypus (SimpleDocTemplate, Table, Paragraph, Drawing) when installed,
and includes a built-in native PDF 1.4 multi-page typesetter so valid multi-page institutional
PDF documents are always generated on disk.
"""

from __future__ import annotations

from pathlib import Path
import textwrap
from typing import Any, Dict, List

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("fmip.reporting.pdf")


def _escape_pdf_text(s: str) -> str:
    """Escape parentheses and backslashes for PDF content streams and normalize to ASCII."""
    ascii_str = (
        s.replace("—", "-")
        .replace("–", "-")
        .replace("“", '"')
        .replace("”", '"')
        .replace("’", "'")
        .replace("‘", "'")
        .replace("•", "*")
        .encode("ascii", errors="replace")
        .decode("ascii")
    )
    return ascii_str.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _generate_native_multipage_pdf(
    output_path: Path,
    report_data: Dict[str, Any],
) -> Path:
    """
    Generate a standards-compliant multi-page PDF 1.4 document with institutional typography,
    headers, footers, 5 Strategic Questions, and all 16 mandatory report sections.
    """
    report_code = str(report_data.get("report_code", "FMIP-WK-REPORT"))
    title = str(report_data.get("title", "Institutional Weekly Financial Intelligence Report"))
    p_start = str(report_data.get("period_start_friday", ""))[:10]
    p_end = str(report_data.get("period_end_friday", ""))[:10]
    five_q = report_data.get("five_strategic_questions", {})
    sections: Dict[str, Any] = report_data.get("sections", {})

    # Collect formatted lines with style tags: ("TITLE" | "H1" | "H2" | "BODY" | "MONO", text)
    styled_lines: List[tuple[str, str]] = [
        ("TITLE", "SOHCAHTOA HOLDINGS LIMITED - INSTITUTIONAL RESEARCH DESK"),
        ("H1", title),
        ("MONO", f"Report Code: {report_code} | Reporting Window: {p_start} to {p_end} (Friday-to-Friday)"),
        ("MONO", "Classification: Executive Decision-Support Intelligence | Geography: Nigeria, Africa & Global"),
        ("BODY", ""),
        ("H2", "EXECUTIVE COMMAND BRIEF: THE FIVE CORE STRATEGIC QUESTIONS"),
    ]

    q_labels = [
        ("q1_where_is_market_currently", "Q1. Where is the financial market currently?"),
        ("q2_what_is_changing_in_market", "Q2. What is changing in the market?"),
        ("q3_where_are_emerging_opportunities", "Q3. Where are the emerging opportunities?"),
        ("q4_what_are_risks_and_threats", "Q4. What are the risks and threats?"),
    ]
    for q_key, q_title in q_labels:
        styled_lines.append(("H2", q_title))
        ans = str(five_q.get(q_key, ""))
        for wrapped in textwrap.wrap(ans, width=92):
            styled_lines.append(("BODY", wrapped))
        styled_lines.append(("BODY", ""))

    styled_lines.append(("H2", "Q5. What strategic actions should our organisation consider?"))
    for act in five_q.get("q5_what_strategic_actions_should_organisation_consider", []):
        for wrapped in textwrap.wrap(str(act), width=90):
            styled_lines.append(("BODY", f"  {wrapped}"))
    styled_lines.append(("BODY", ""))

    # Render all 16 mandatory sections
    ordered_keys = sorted(sections.keys())
    for sec_key in ordered_keys:
        sec = sections[sec_key]
        sec_title = str(sec.get("title", sec_key))
        styled_lines.append(("H1", sec_title.upper()))
        narrative = str(sec.get("narrative", ""))
        for para in narrative.split("\n"):
            p_clean = para.strip()
            if not p_clean:
                continue
            for wrapped in textwrap.wrap(p_clean, width=92):
                styled_lines.append(("BODY", wrapped))

        # Include key tabular rows if present
        for tbl_key in (
            "performance_table",
            "global_benchmarks",
            "equity_valuation_table",
            "approved_investment_opportunities",
            "strategic_opportunities",
            "calendar_events",
            "recommendations",
            "source_register",
        ):
            rows = sec.get(tbl_key)
            if isinstance(rows, list) and rows:
                styled_lines.append(("H2", f"Table: {tbl_key.replace('_', ' ').title()}"))
                for item in rows[:12]:
                    if isinstance(item, dict):
                        summary_pairs = [
                            f"{k}: {v}"
                            for k, v in list(item.items())[:5]
                            if not isinstance(v, (dict, list))
                        ]
                        row_line = " | ".join(summary_pairs)
                        for wrapped in textwrap.wrap(row_line, width=95):
                            styled_lines.append(("MONO", f"  {wrapped}"))
        styled_lines.append(("BODY", ""))

    # Paginate styled_lines (46 lines per A4 page)
    lines_per_page = 46
    pages: List[List[tuple[str, str]]] = [
        styled_lines[i : i + lines_per_page]
        for i in range(0, len(styled_lines), lines_per_page)
    ] or [[("TITLE", title)]]

    # Build PDF objects:
    # 1: Catalog, 2: Pages, 3: Font Helvetica, 4: Font Helvetica-Bold, 5: Font Courier
    objects: List[bytes] = []

    def add_obj(content: bytes) -> int:
        objects.append(content)
        return len(objects)

    add_obj(b"<< /Type /Catalog /Pages 2 0 R >>")  # Obj 1
    add_obj(b"")  # Obj 2 placeholder for Pages
    add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")  # Obj 3
    add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")  # Obj 4
    add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")  # Obj 5

    page_obj_ids: List[int] = []
    total_pages = len(pages)

    for page_idx, page_lines in enumerate(pages, start=1):
        stream_cmds: List[str] = [
            "BT",
            "/F2 8 Tf",
            "50 805 Td",
            f"({_escape_pdf_text(f'SOHCAHTOA FMIP | {report_code} | INSTITUTIONAL FINANCIAL MARKETS INTELLIGENCE')}) Tj",
            "ET",
        ]
        y_cursor = 782
        for style, txt in page_lines:
            esc = _escape_pdf_text(txt)
            if style == "TITLE":
                font_cmd = "/F2 12 Tf"
                step = 16
            elif style == "H1":
                font_cmd = "/F2 10.5 Tf"
                step = 15
            elif style == "H2":
                font_cmd = "/F2 9.5 Tf"
                step = 13
            elif style == "MONO":
                font_cmd = "/F3 8 Tf"
                step = 12
            else:
                font_cmd = "/F1 9 Tf"
                step = 12.5

            stream_cmds.extend(
                [
                    "BT",
                    font_cmd,
                    f"50 {y_cursor:.1f} Td",
                    f"({esc}) Tj",
                    "ET",
                ]
            )
            y_cursor -= step

        # Footer
        stream_cmds.extend(
            [
                "BT",
                "/F3 8 Tf",
                "50 32 Td",
                f"({_escape_pdf_text(f'Page {page_idx} of {total_pages} | Verified by Agent 8 (Chief Research Editor) & Agent 6 (Python Quant Engine)')}) Tj",
                "ET",
            ]
        )

        stream_bytes = "\n".join(stream_cmds).encode("ascii", errors="replace")
        content_obj_id = add_obj(
            f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("ascii")
            + stream_bytes
            + b"\nendstream"
        )
        page_dict = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R >> >> "
            f"/Contents {content_obj_id} 0 R >>"
        ).encode("ascii")
        page_obj_id = add_obj(page_dict)
        page_obj_ids.append(page_obj_id)

    kids_str = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
    objects[1] = f"<< /Type /Pages /Kids [{kids_str}] /Count {len(page_obj_ids)} >>".encode(
        "ascii"
    )

    # Assemble binary PDF with xref table
    buf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: List[int] = [0]
    for idx, obj_bytes in enumerate(objects, start=1):
        offsets.append(len(buf))
        buf.extend(f"{idx} 0 obj\n".encode("ascii"))
        buf.extend(obj_bytes)
        buf.extend(b"\nendobj\n")

    xref_offset = len(buf)
    buf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    buf.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        buf.extend(f"{off:010d} 00000 n \n".encode("ascii"))

    buf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(bytes(buf))
    return output_path


def generate_weekly_report_pdf(
    report_data: Dict[str, Any],
    output_dir: str | Path | None = None,
) -> Path:
    """
    Generate the 16-section institutional PDF report for a Weekly Intelligence Report.
    Uses ReportLab Platypus when available or the built-in multi-page PDF 1.4 engine.
    """
    base_dir = Path(output_dir or settings.REPORT_STORAGE_DIR) / "pdf"
    base_dir.mkdir(parents=True, exist_ok=True)
    report_code = str(report_data.get("report_code", "FMIP-WK-REPORT"))
    output_path = base_dir / f"{report_code}.pdf"

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=42,
            bottomMargin=42,
            title=str(report_data.get("title", report_code)),
            author="SohCahToa Financial Markets Intelligence Platform",
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "InstTitle",
            parent=styles["Heading1"],
            fontSize=15,
            leading=19,
            textColor=colors.HexColor("#064e3b"),
            spaceAfter=8,
        )
        h1_style = ParagraphStyle(
            "InstH1",
            parent=styles["Heading2"],
            fontSize=11.5,
            leading=15,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=12,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "InstBody",
            parent=styles["BodyText"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=6,
        )

        story: List[Any] = [
            Paragraph(
                "SOHCAHTOA HOLDINGS LIMITED — INSTITUTIONAL FINANCIAL RESEARCH DESK",
                h1_style,
            ),
            Paragraph(str(report_data.get("title", report_code)), title_style),
            Paragraph(
                f"<b>Report Code:</b> {report_code} | "
                f"<b>Reporting Window:</b> {str(report_data.get('period_start_friday', ''))[:10]} to "
                f"{str(report_data.get('period_end_friday', ''))[:10]}",
                body_style,
            ),
            Spacer(1, 10),
        ]

        sections: Dict[str, Any] = report_data.get("sections", {})
        for sec_key in sorted(sections.keys()):
            sec = sections[sec_key]
            story.append(Paragraph(str(sec.get("title", sec_key)), h1_style))
            for para in str(sec.get("narrative", "")).split("\n"):
                if para.strip():
                    story.append(Paragraph(para.strip(), body_style))

            # Render key tables with ReportLab Table
            for tbl_key in ("performance_table", "equity_valuation_table", "calendar_events"):
                rows = sec.get(tbl_key)
                if isinstance(rows, list) and rows and isinstance(rows[0], dict):
                    headers = list(rows[0].keys())[:6]
                    tbl_data = [headers]
                    for r in rows[:12]:
                        tbl_data.append([str(r.get(h, ""))[:28] for h in headers])
                    t = Table(tbl_data, repeatRows=1)
                    t.setStyle(
                        TableStyle(
                            [
                                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                            ]
                        )
                    )
                    story.append(t)
                    story.append(Spacer(1, 8))

        doc.build(story)
        logger.info("Generated ReportLab 16-section PDF report at %s", output_path)
        return output_path
    except Exception as exc:
        logger.info("Using built-in native PDF 1.4 multi-page generator (%s)", exc)
        return _generate_native_multipage_pdf(output_path, report_data)
