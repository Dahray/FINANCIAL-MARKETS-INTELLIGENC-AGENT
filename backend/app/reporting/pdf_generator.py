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
    Generate the institutional multi-section Weekly Financial Markets Intelligence PDF report.
    Uses ReportLab Platypus + embedded verified Matplotlib PNG charts when available,
    falling back to the built-in multi-page PDF 1.4 engine if ReportLab is unavailable.
    """
    base_dir = Path(output_dir or settings.REPORT_STORAGE_DIR) / "pdf"
    base_dir.mkdir(parents=True, exist_ok=True)
    report_code = str(report_data.get("report_code", "FMIP-WK-REPORT"))
    output_path = base_dir / f"{report_code}.pdf"

    try:
        from html import escape as html_escape
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            HRFlowable,
            Image as RLImage,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        from app.reporting.chart_generator import generate_verified_report_charts

        sections: Dict[str, Any] = report_data.get("sections", {})
        chart_series = report_data.get("chart_series_payload", {})
        charts_map = generate_verified_report_charts(
            report_code=report_code,
            sections=sections,
            chart_series=chart_series,
            output_dir=Path(output_dir or settings.REPORT_STORAGE_DIR),
        )

        BRAND_ORANGE = colors.HexColor("#EA580C")
        BRAND_ORANGE_DARK = colors.HexColor("#C2410C")
        BRAND_CHARCOAL = colors.HexColor("#1C1917")
        NAVY = BRAND_ORANGE_DARK
        EMERALD = BRAND_ORANGE
        EMERALD_ACCENT = BRAND_ORANGE
        SLATE_TEXT = colors.HexColor("#292524")
        MUTED = colors.HexColor("#78716C")
        LIGHT_BG = colors.HexColor("#FFF7ED")
        BORDER_CLR = colors.HexColor("#FED7AA")
        POS_BG = colors.HexColor("#DCFCE7")
        POS_FG = colors.HexColor("#166534")
        NEG_BG = colors.HexColor("#FEE2E2")
        NEG_FG = colors.HexColor("#991B1B")

        def _on_page(canvas, doc_obj):
            canvas.saveState()
            w, h = A4
            canvas.setStrokeColor(BRAND_ORANGE)
            canvas.setLineWidth(1.5)
            canvas.line(36, h - 28, w - 36, h - 28)
            canvas.setFont("Helvetica-Bold", 7.5)
            canvas.setFillColor(BRAND_ORANGE_DARK)
            canvas.drawString(36, h - 23, f"SOHCAHTOA HOLDINGS LIMITED  |  INSTITUTIONAL RESEARCH DESK  |  {report_code}")
            canvas.setStrokeColor(BORDER_CLR)
            canvas.setLineWidth(0.7)
            canvas.line(36, 30, w - 36, 30)
            canvas.setFont("Helvetica", 7.2)
            canvas.setFillColor(MUTED)
            canvas.drawString(36, 19, "SohCahToa Verified Source-of-Truth Intelligence | Supervised by Agent 8 (Chief Editor) & Agent 6 (Quant Engine)")
            canvas.drawRightString(w - 36, 19, f"Page {doc_obj.page}")
            canvas.restoreState()

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=44,
            bottomMargin=42,
            title=str(report_data.get("title", report_code)),
            author="SohCahToa Financial Markets Intelligence Platform",
        )
        styles = getSampleStyleSheet()
        cover_sub = ParagraphStyle("CoverSub", parent=styles["Normal"], fontSize=8.5, leading=12, textColor=colors.HexColor("#FFEDD5"), spaceAfter=4, fontName="Helvetica-Bold")
        cover_title = ParagraphStyle("CoverTitle", parent=styles["Heading1"], fontSize=16.5, leading=21, textColor=colors.white, spaceAfter=6)
        cover_meta = ParagraphStyle("CoverMeta", parent=styles["Normal"], fontSize=8.5, leading=12, textColor=colors.HexColor("#FFF7ED"))
        h1_style = ParagraphStyle("InstH1", parent=styles["Heading2"], fontSize=11.5, leading=15, textColor=BRAND_ORANGE_DARK, spaceBefore=12, spaceAfter=4)
        h2_style = ParagraphStyle("InstH2", parent=styles["Heading3"], fontSize=9.5, leading=13, textColor=BRAND_CHARCOAL, spaceBefore=8, spaceAfter=3)
        body_style = ParagraphStyle("InstBody", parent=styles["BodyText"], fontSize=8.6, leading=12.4, textColor=SLATE_TEXT, spaceAfter=5)
        small_cell = ParagraphStyle("SmallCell", parent=styles["Normal"], fontSize=7.2, leading=9.5, textColor=SLATE_TEXT)
        header_cell = ParagraphStyle("HeaderCell", parent=styles["Normal"], fontSize=7.4, leading=9.5, textColor=colors.white, fontName="Helvetica-Bold")
        caption_style = ParagraphStyle("Caption", parent=styles["Normal"], fontSize=7.0, leading=9.5, textColor=MUTED, spaceAfter=6, fontName="Helvetica-Oblique")

        def _p(text: Any, style=body_style) -> Paragraph:
            return Paragraph(html_escape(str(text or "")).replace("\n", "<br/>"), style)

        def _fmt_pct(v: Any) -> str:
            if v is None or v == "":
                return "—"
            try:
                return f"{float(v):+.2f}%"
            except Exception:
                return str(v)

        def _fmt_bps(v: Any) -> str:
            if v is None or v == "":
                return "—"
            try:
                return f"{float(v):+.0f} bps"
            except Exception:
                return str(v)

        def _build_styled_table(
            headers: List[str],
            rows: List[List[str]],
            col_widths: List[float] | None = None,
            signed_cols: List[int] | None = None,
            invert_sign_color: bool = False,
            caption: str = "",
        ) -> List[Any]:
            if not rows:
                return []
            tbl_data = [[Paragraph(html_escape(h), header_cell) for h in headers]]
            style_cmds: List[Any] = [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.35, BORDER_CLR),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
            ]
            signed_set = set(signed_cols or [])
            for r_i, row_vals in enumerate(rows, start=1):
                row_cells = []
                for c_i, val_s in enumerate(row_vals):
                    cell_txt = str(val_s)
                    if c_i in signed_set and (cell_txt.startswith("+") or cell_txt.startswith("-")):
                        is_pos = cell_txt.startswith("+")
                        good = (not is_pos) if invert_sign_color else is_pos
                        bg = POS_BG if good else NEG_BG
                        fg = POS_FG if good else NEG_FG
                        style_cmds.append(("BACKGROUND", (c_i, r_i), (c_i, r_i), bg))
                        c_style = ParagraphStyle(f"sc_{r_i}_{c_i}", parent=small_cell, textColor=fg, fontName="Helvetica-Bold")
                        row_cells.append(Paragraph(html_escape(cell_txt), c_style))
                    else:
                        row_cells.append(Paragraph(html_escape(cell_txt), small_cell))
                tbl_data.append(row_cells)

            t = Table(tbl_data, colWidths=col_widths, repeatRows=1)
            t.setStyle(TableStyle(style_cmds))
            elems: List[Any] = [t]
            if caption:
                elems.append(Paragraph(html_escape(caption), caption_style))
            elems.append(Spacer(1, 6))
            return elems

        def _add_chart(chart_key: str, width_in: float = 7.1) -> List[Any]:
            p = charts_map.get(chart_key)
            if not p or not p.exists():
                return []
            return [RLImage(str(p), width=width_in * inch, height=(width_in * 0.455) * inch), Spacer(1, 6)]

        # Executive Cover Banner
        banner_tbl = Table(
            [
                [
                    Paragraph("SOHCAHTOA HOLDINGS LIMITED  •  AI FINANCIAL MARKETS INTELLIGENCE PLATFORM", cover_sub),
                ],
                [
                    Paragraph(html_escape(str(report_data.get("title", report_code))), cover_title),
                ],
                [
                    Paragraph(
                        f"<b>Report Code:</b> {html_escape(report_code)}   |   "
                        f"<b>Window:</b> {html_escape(str(report_data.get('period_start_friday', ''))[:10])} to "
                        f"{html_escape(str(report_data.get('period_end_friday', ''))[:10])}   |   "
                        f"<b>Verified Charts Embedded:</b> {len(charts_map)}",
                        cover_meta,
                    ),
                ],
            ],
            colWidths=[523],
        )
        banner_tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                    ("LEFTPADDING", (0, 0), (-1, -1), 14),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                    ("TOPPADDING", (0, 0), (0, 0), 12),
                    ("BOTTOMPADDING", (0, -1), (-1, -1), 12),
                    ("LINEBELOW", (0, -1), (-1, -1), 3, EMERALD_ACCENT),
                ]
            )
        )

        story: List[Any] = [banner_tbl, Spacer(1, 10)]

        # Five Core Strategic Questions Box
        five_q = report_data.get("five_strategic_questions", {})
        if five_q:
            story.append(Paragraph("EXECUTIVE COMMAND BRIEF — THE FIVE CORE STRATEGIC QUESTIONS", h1_style))
            story.append(HRFlowable(width="100%", thickness=0.8, color=EMERALD_ACCENT, spaceAfter=6))
            for qk, qlbl in [
                ("q1_where_is_market_currently", "1. Where is the financial market currently?"),
                ("q2_what_is_changing_in_market", "2. What is changing in the market?"),
                ("q3_where_are_emerging_opportunities", "3. Where are the emerging opportunities?"),
                ("q4_what_are_risks_and_threats", "4. What are the risks and threats?"),
            ]:
                if five_q.get(qk):
                    story.append(Paragraph(f"<b>{html_escape(qlbl)}</b>", h2_style))
                    story.append(_p(five_q[qk]))
            actions = five_q.get("q5_what_strategic_actions_should_organisation_consider", [])
            if actions:
                story.append(Paragraph("<b>5. What strategic actions should our organisation consider?</b>", h2_style))
                for act in actions:
                    story.append(_p(f"• {act}"))
            story.append(Spacer(1, 6))

        # Render all sections with dedicated tables & embedded verified charts
        for sec_key in sorted(sections.keys()):
            sec = sections[sec_key]
            story.append(Paragraph(html_escape(str(sec.get("title", sec_key))), h1_style))
            story.append(HRFlowable(width="100%", thickness=0.6, color=BORDER_CLR, spaceAfter=5))
            for para in str(sec.get("narrative", "")).split("\n"):
                if para.strip():
                    story.append(_p(para.strip()))

            # Section 02: Nigerian Equities & Moving Averages Chart
            if sec_key == "section_02_nigerian_financial_market_performance":
                ng_dash = sec.get("nigerian_equities_dashboard", {})
                tracked = ng_dash.get("tracked_equities", [])
                if tracked:
                    story.extend(
                        _build_styled_table(
                            ["Ticker", "Security", "Price", "WTD (%)", "MTD (%)", "YTD (%)", "Regime / Freshness"],
                            [
                                [
                                    r["symbol"],
                                    r["name"][:24],
                                    f"{r['price']:,.2f}",
                                    _fmt_pct(r.get("wtd_pct")),
                                    _fmt_pct(r.get("mtd_pct")),
                                    _fmt_pct(r.get("ytd_pct")),
                                    f"{r.get('technical_regime', '')} ({r.get('freshness_status', '')})"[:28],
                                ]
                                for r in tracked[:10]
                            ],
                            col_widths=[62, 118, 56, 48, 48, 48, 143],
                            signed_cols=[3, 4, 5],
                            caption=f"Source: NGX / FMIP DB | Note: {ng_dash.get('data_governance_note', '')}",
                        )
                    )
                story.extend(_add_chart("equity_moving_averages"))

            # Section 03: Global Stock Market Indices & Global Performance Chart
            if sec_key == "section_03_global_market_performance":
                geq = sec.get("global_equities_table", [])
                if geq:
                    story.append(Paragraph("Selected Global Stock Market Indices (Live Verified EOD)", h2_style))
                    story.extend(
                        _build_styled_table(
                            ["Index", "Country", "Latest", "WTD (%)", "MTD (%)", "YTD (%)", "Technical Regime"],
                            [
                                [
                                    r["name"],
                                    r["country_or_unit"],
                                    f"{r['price']:,.2f}",
                                    _fmt_pct(r.get("wtd_pct")),
                                    _fmt_pct(r.get("mtd_pct")),
                                    _fmt_pct(r.get("ytd_pct")),
                                    str(r.get("technical_regime", ""))[:22],
                                ]
                                for r in geq
                            ],
                            col_widths=[100, 72, 62, 52, 52, 52, 133],
                            signed_cols=[3, 4, 5],
                            caption="Source: Financial Modeling Prep (/stable/quote & EOD History) | Basis: Calendar WTD, MTD & YTD Returns",
                        )
                    )
                story.extend(_add_chart("global_performance"))

            # Section 04: Global & Nigerian Macro + US Labour Chart + Cross-Market Transmission
            if sec_key == "section_04_macroeconomic_developments":
                story.extend(_add_chart("us_labour"))
                cmat = sec.get("cross_market_transmission_matrix", [])
                if cmat:
                    story.append(Paragraph("Cross-Market Transmission Analysis (Correlation vs Mechanism vs Causal Evidence)", h2_style))
                    story.extend(
                        _build_styled_table(
                            ["Transmission Channel", "Observed Correlation", "Plausible Mechanism", "Empirical Evidence & Caveats"],
                            [
                                [
                                    c["channel"],
                                    c["observed_correlation"],
                                    c["plausible_transmission_mechanism"],
                                    c["causal_evidence_and_caveats"],
                                ]
                                for c in cmat
                            ],
                            col_widths=[115, 92, 166, 150],
                            caption="Source: Agent 6 Econometrics + Agent 2 Macro Analysis | Epistemic standard: Correlation strictly separated from causation",
                        )
                    )

            # Section 05: Global 10Y Bonds + CBN NTB/OMO/FGN Auctions + 2 Fixed Income Charts
            if sec_key == "section_05_fixed_income_market_analysis":
                g10 = sec.get("global_10y_bonds_table", [])
                if g10:
                    story.append(Paragraph("Global 10-Year Sovereign Government Bond Yields (FRED / OECD Tier-1)", h2_style))
                    story.extend(
                        _build_styled_table(
                            ["Country", "Yield (%)", "WTD", "MTD", "YTD", "YoY", "As Of"],
                            [
                                [
                                    r["country"],
                                    f"{r['yield_pct']:.2f}%" if r.get("yield_pct") is not None else "—",
                                    _fmt_bps(r.get("wtd_bps")),
                                    _fmt_bps(r.get("mtd_bps")),
                                    _fmt_bps(r.get("ytd_bps")),
                                    _fmt_bps(r.get("yoy_bps")),
                                    r.get("as_of_date", ""),
                                ]
                                for r in g10
                            ],
                            col_widths=[100, 58, 68, 68, 68, 68, 93],
                            signed_cols=[2, 3, 4, 5],
                            invert_sign_color=True,
                            caption="Source: St. Louis Fed FRED / OECD Tier-1 | Units: % & Basis Points (Green = Yield Decline / Bond Rally)",
                        )
                    )
                story.extend(_add_chart("global_10y_bonds"))

                fi_auc = sec.get("nigerian_fixed_income_auctions", {})
                auc_rows = (fi_auc.get("ntb_auctions", [])[:5]) + (fi_auc.get("omo_auctions", [])[:5])
                if auc_rows:
                    story.append(Paragraph("Live Central Bank of Nigeria (CBN) NTB & OMO Primary Auctions", h2_style))
                    story.extend(
                        _build_styled_table(
                            ["Instrument", "Tenor", "Stop Rate (%)", "Bid-to-Cover", "Auction Date"],
                            [
                                [
                                    a["instrument"],
                                    a["tenor"],
                                    f"{a['stop_rate_pct']:.2f}%",
                                    f"{a['bid_to_cover']:.2f}x" if a.get("bid_to_cover") is not None else "—",
                                    a["auction_date"],
                                ]
                                for a in auc_rows
                            ],
                            col_widths=[95, 75, 100, 105, 148],
                            caption=f"Source: CBN Tier-1 Official APIs (GetAllSecuritiesNTB & GetAllSecuritiesOMO) | {fi_auc.get('eurobond_feed_status', '')}",
                        )
                    )
                story.extend(_add_chart("nigeria_yield_curves"))

            # Section 06: Major Currencies + Commodities + Reserves vs NFEM Chart
            if sec_key == "section_06_fx_market_analysis":
                fx_tbl = sec.get("major_currencies_table", [])
                if fx_tbl:
                    story.append(Paragraph("Major Global & African Currencies Performance", h2_style))
                    story.extend(
                        _build_styled_table(
                            ["Currency", "Country", "Price", "WTD (%)", "MTD (%)", "YTD (%)", "YoY (%)"],
                            [
                                [
                                    r["name"],
                                    r["country_or_unit"],
                                    f"{r['price']:,.4f}" if r["price"] < 20 else f"{r['price']:,.2f}",
                                    _fmt_pct(r.get("wtd_pct")),
                                    _fmt_pct(r.get("mtd_pct")),
                                    _fmt_pct(r.get("ytd_pct")),
                                    _fmt_pct(r.get("yoy_pct")),
                                ]
                                for r in fx_tbl
                            ],
                            col_widths=[115, 78, 70, 65, 65, 65, 65],
                            signed_cols=[3, 4, 5, 6],
                            caption="Source: CBN Official NFEM API & St. Louis Fed FRED Tier-1 FX Series | Basis: Spot / Daily Closing Rates",
                        )
                    )
                story.extend(_add_chart("reserves_vs_nfem"))

                cmd_tbl = sec.get("commodities_table", [])
                if cmd_tbl:
                    story.append(Paragraph("Global & Nigerian Commodity Benchmarks", h2_style))
                    story.extend(
                        _build_styled_table(
                            ["Commodity", "Unit", "Price", "Daily (%)", "WTD (%)", "MTD (%)", "YTD (%)"],
                            [
                                [
                                    r["name"],
                                    r["country_or_unit"],
                                    f"{r['price']:,.2f}",
                                    _fmt_pct(r.get("daily_pct")),
                                    _fmt_pct(r.get("wtd_pct")),
                                    _fmt_pct(r.get("mtd_pct")),
                                    _fmt_pct(r.get("ytd_pct")),
                                ]
                                for r in cmd_tbl
                            ],
                            col_widths=[125, 68, 70, 65, 65, 65, 65],
                            signed_cols=[3, 4, 5, 6],
                            caption="Source: CBN Crude Oil API, St. Louis Fed FRED (Brent/NatGas/Copper) & FMP (Gold/Silver)",
                        )
                    )

            # Section 08 / 11: Asset-Class Implications (Findings vs Theses)
            if sec_key == "section_08_financial_services_industry_intelligence":
                imp = sec.get("asset_class_implications", [])
                if imp:
                    story.append(Paragraph("Asset-Class & Business-Line Implications Matrix (Findings vs Investment Theses)", h2_style))
                    story.extend(
                        _build_styled_table(
                            ["Asset Class / Desk", "Verified Research Finding", "Investment Thesis & Drivers", "Key Risks & Invalidation", "Horizon / Conf."],
                            [
                                [
                                    i["asset_class_or_business_line"],
                                    i["research_finding"],
                                    f"{i['investment_thesis']} Drivers: {i['return_drivers']}",
                                    f"Risks: {i['key_risks']} | Invalidated if: {i['invalidation_conditions']}",
                                    f"{i['time_horizon']} | {i['confidence_level']}",
                                ]
                                for i in imp
                            ],
                            col_widths=[90, 118, 125, 122, 68],
                            caption="Source: FMIP Research Desk | Research findings are strictly separated from actionable investment theses.",
                        )
                    )

            # Section 14: Structured Week-Ahead Economic Calendar (Global + Nigeria)
            if sec_key == "section_14_next_week_economic_and_financial_calendar":
                cal_ev = sec.get("calendar_events", [])
                if cal_ev:
                    story.extend(
                        _build_styled_table(
                            ["Region / Country", "Event / Catalyst", "Previous (Verified)", "Expectation / Watch", "Date", "Market Implication"],
                            [
                                [
                                    f"{e.get('region', '')} ({e.get('country', '')})",
                                    e.get("event", ""),
                                    e.get("previous", "—"),
                                    e.get("expectation", "—"),
                                    e.get("date", ""),
                                    e.get("market_implication", ""),
                                ]
                                for e in cal_ev[:10]
                            ],
                            col_widths=[74, 96, 80, 92, 54, 127],
                            caption="Source: FMIP Economic Calendar anchored to verified DB previous readings | Actuals updated upon official publication",
                        )
                    )

            # Fallback generic tables for valuation / source register
            for tbl_key in ("equity_valuation_table", "source_register"):
                rows = sec.get(tbl_key)
                if isinstance(rows, list) and rows and isinstance(rows[0], dict):
                    headers = list(rows[0].keys())[:5]
                    tbl_rows = [[str(r.get(h, ""))[:36] for h in headers] for r in rows[:12]]
                    story.extend(_build_styled_table(headers, tbl_rows))

        doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
        logger.info("Generated institutional ReportLab PDF report with %d charts at %s", len(charts_map), output_path)
        return output_path
    except Exception as exc:
        logger.info("Using built-in native PDF 1.4 multi-page generator (%s)", exc)
        return _generate_native_multipage_pdf(output_path, report_data)
