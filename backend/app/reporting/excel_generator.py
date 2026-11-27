"""
Institutional Multi-Sheet Excel Financial Data Workbook Generator (Section 7).
Uses OpenPyXL (`openpyxl`) to generate an 8-worksheet formatted institutional workbook
containing all underlying market data, sovereign yield curves, macro indicators,
2-stage DCF equity valuations, walk-forward backtested forecasts, Opportunity Radar rankings,
and the complete Source Register.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("fmip.reporting.excel")


HEADER_FILL = PatternFill(start_color="C2410C", end_color="C2410C", fill_type="solid")
SUBHEADER_FILL = PatternFill(start_color="EA580C", end_color="EA580C", fill_type="solid")
ALT_ROW_FILL = PatternFill(start_color="FFF7ED", end_color="FFF7ED", fill_type="solid")

HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
TITLE_FONT = Font(name="Calibri", size=14, bold=True, color="9A3412")
BOLD_FONT = Font(name="Calibri", size=10, bold=True, color="1C1917")
REGULAR_FONT = Font(name="Calibri", size=10, bold=False, color="292524")

THIN_BORDER = Border(
    left=Side(style="thin", color="FED7AA"),
    right=Side(style="thin", color="FED7AA"),
    top=Side(style="thin", color="FED7AA"),
    bottom=Side(style="thin", color="FED7AA"),
)


def _auto_fit_columns(ws) -> None:
    """Auto-adjust column widths for clean institutional presentation."""
    for col in ws.columns:
        max_len = 12
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = min(55, len(val_str))
        ws.column_dimensions[col_letter].width = max_len + 4


def _write_table_to_sheet(
    ws,
    start_row: int,
    headers: List[str],
    rows: List[List[Any]],
) -> int:
    """Write a styled institutional table to an OpenPyXL worksheet and return next row index."""
    for c_idx, h_text in enumerate(headers, start=1):
        cell = ws.cell(row=start_row, column=c_idx, value=h_text)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER

    curr_row = start_row + 1
    for r_idx, row_vals in enumerate(rows):
        for c_idx, val in enumerate(row_vals, start=1):
            cell = ws.cell(row=curr_row, column=c_idx, value=val)
            cell.font = REGULAR_FONT
            cell.border = THIN_BORDER
            if r_idx % 2 == 1:
                cell.fill = ALT_ROW_FILL
            if isinstance(val, (int, float)):
                cell.number_format = "#,##0.00"
        curr_row += 1
    return curr_row + 1


def generate_weekly_report_excel(
    report_data: Dict[str, Any],
    output_dir: str | Path | None = None,
) -> Path:
    """
    Generate an 8-sheet Excel workbook containing all underlying financial data
    for a Friday Weekly Intelligence Report.
    """
    base_dir = Path(output_dir or settings.REPORT_STORAGE_DIR) / "excel"
    base_dir.mkdir(parents=True, exist_ok=True)
    report_code = str(report_data.get("report_code", "FMIP-WK-REPORT"))
    output_path = base_dir / f"{report_code}.xlsx"

    wb = openpyxl.Workbook()
    sections = report_data.get("sections", {})
    five_q = report_data.get("five_strategic_questions", {})

    # --------------------------------------------------------------------------
    # Sheet 1: 01_Executive_Summary
    # --------------------------------------------------------------------------
    ws1 = wb.active
    ws1.title = "01_Executive_Summary"
    ws1["A1"] = "SOHCAHTOA HOLDINGS LIMITED — FINANCIAL MARKETS INTELLIGENCE PLATFORM"
    ws1["A1"].font = TITLE_FONT
    ws1["A2"] = f"Report Code: {report_code} | Title: {report_data.get('title', '')}"
    ws1["A2"].font = BOLD_FONT
    ws1["A4"] = "Executive Summary"
    ws1["A4"].font = BOLD_FONT
    ws1["A5"] = str(report_data.get("executive_summary", ""))
    ws1["A5"].alignment = Alignment(wrap_text=True)

    q_rows = [
        ["1. Where is the financial market currently?", five_q.get("q1_where_is_market_currently", "")],
        ["2. What is changing in the market?", five_q.get("q2_what_is_changing_in_market", "")],
        ["3. Where are the emerging opportunities?", five_q.get("q3_where_are_emerging_opportunities", "")],
        ["4. What are the risks and threats?", five_q.get("q4_what_are_risks_and_threats", "")],
        [
            "5. What strategic actions should our organisation consider?",
            "\n".join(five_q.get("q5_what_strategic_actions_should_organisation_consider", [])),
        ],
    ]
    _write_table_to_sheet(ws1, 7, ["Core Strategic Question", "Executive Synthesis"], q_rows)
    _auto_fit_columns(ws1)

    # --------------------------------------------------------------------------
    # Sheet 2: 02_Market_Performance
    # --------------------------------------------------------------------------
    ws2 = wb.create_sheet("02_Market_Performance")
    ws2["A1"] = "Nigerian & Global Financial Market Performance Summary"
    ws2["A1"].font = TITLE_FONT
    ng_perf = sections.get("section_02_nigerian_financial_market_performance", {}).get(
        "performance_table", []
    )
    gl_perf = sections.get("section_03_global_market_performance", {}).get(
        "global_benchmarks", []
    )
    all_perf = ng_perf + [g for g in gl_perf if g not in ng_perf]
    perf_rows = [
        [
            m.get("symbol"),
            m.get("name"),
            m.get("latest"),
            m.get("unit"),
            m.get("return_1w_pct"),
            m.get("return_1m_pct"),
            m.get("volatility_ann_pct"),
        ]
        for m in all_perf
    ]
    next_r = _write_table_to_sheet(
        ws2,
        3,
        [
            "Symbol",
            "Instrument Name",
            "Latest Close",
            "Unit",
            "1W Return (%)",
            "1M Return (%)",
            "Annualized Vol (%)",
        ],
        perf_rows,
    )

    # Global Stock Indices (WTD / MTD / YTD)
    gl_eq = sections.get("section_03_global_market_performance", {}).get("global_equities_table", [])
    if gl_eq:
        ws2.cell(row=next_r, column=1, value="Selected Global Stock Market Indices (Live Verified EOD)").font = BOLD_FONT
        next_r = _write_table_to_sheet(
            ws2,
            next_r + 1,
            ["Symbol", "Index", "Country", "Price", "WTD (%)", "MTD (%)", "YTD (%)", "Technical Regime"],
            [
                [r.get("symbol"), r.get("name"), r.get("country_or_unit"), r.get("price"), r.get("wtd_pct"), r.get("mtd_pct"), r.get("ytd_pct"), r.get("technical_regime")]
                for r in gl_eq
            ],
        )

    # Major Currencies & Commodities
    fx_tbl = sections.get("section_06_fx_market_analysis", {}).get("major_currencies_table", [])
    if fx_tbl:
        ws2.cell(row=next_r, column=1, value="Major Global & African Currencies").font = BOLD_FONT
        next_r = _write_table_to_sheet(
            ws2,
            next_r + 1,
            ["Pair", "Currency", "Country", "Price", "WTD (%)", "MTD (%)", "YTD (%)", "YoY (%)"],
            [
                [r.get("symbol"), r.get("name"), r.get("country_or_unit"), r.get("price"), r.get("wtd_pct"), r.get("mtd_pct"), r.get("ytd_pct"), r.get("yoy_pct")]
                for r in fx_tbl
            ],
        )

    cmd_tbl = sections.get("section_06_fx_market_analysis", {}).get("commodities_table", [])
    if cmd_tbl:
        ws2.cell(row=next_r, column=1, value="Global & Nigerian Commodity Benchmarks").font = BOLD_FONT
        _write_table_to_sheet(
            ws2,
            next_r + 1,
            ["Symbol", "Commodity", "Unit", "Price", "Daily (%)", "WTD (%)", "MTD (%)", "YTD (%)"],
            [
                [r.get("symbol"), r.get("name"), r.get("country_or_unit"), r.get("price"), r.get("daily_pct"), r.get("wtd_pct"), r.get("mtd_pct"), r.get("ytd_pct")]
                for r in cmd_tbl
            ],
        )
    _auto_fit_columns(ws2)

    # --------------------------------------------------------------------------
    # Sheet 3: 03_Sovereign_Yield_Curve
    # --------------------------------------------------------------------------
    ws3 = wb.create_sheet("03_Sovereign_Yield_Curve")
    ws3["A1"] = "Nigerian Sovereign Yield Curve, Live CBN NTB/OMO Auctions & Global 10Y Bonds"
    ws3["A1"].font = TITLE_FONT
    sec5 = sections.get("section_05_fixed_income_market_analysis", {})
    yc = sec5.get("yield_curve_analytics", {})
    fitted = yc.get("fitted_standard_tenors", {})
    fisher = yc.get("real_yields_fisher_pct", {})
    simple = yc.get("simple_real_spreads_pct", {})
    yc_rows = [
        [tenor, nom_val, fisher.get(tenor), simple.get(tenor), yc.get("inflation_benchmark_pct")]
        for tenor, nom_val in fitted.items()
    ]
    next_r3 = _write_table_to_sheet(
        ws3,
        3,
        [
            "Tenor",
            "Nelson-Siegel Nominal Yield (%)",
            "Fisher Exact Real Yield (%)",
            "Simple Real Spread (%)",
            "Inflation Benchmark (%)",
        ],
        yc_rows,
    )

    g10 = sec5.get("global_10y_bonds_table", [])
    if g10:
        ws3.cell(row=next_r3, column=1, value="Global 10-Year Sovereign Government Bond Yields (FRED / OECD Tier-1)").font = BOLD_FONT
        next_r3 = _write_table_to_sheet(
            ws3,
            next_r3 + 1,
            ["Country", "Yield (%)", "WTD (bps)", "MTD (bps)", "YTD (bps)", "YoY (bps)", "As Of"],
            [
                [r.get("country"), r.get("yield_pct"), r.get("wtd_bps"), r.get("mtd_bps"), r.get("ytd_bps"), r.get("yoy_bps"), r.get("as_of_date")]
                for r in g10
            ],
        )

    fi_auc = sec5.get("nigerian_fixed_income_auctions", {})
    auc_rows = fi_auc.get("ntb_auctions", []) + fi_auc.get("omo_auctions", [])
    if auc_rows:
        ws3.cell(row=next_r3, column=1, value="Live Central Bank of Nigeria (CBN) NTB & OMO Primary Auctions").font = BOLD_FONT
        _write_table_to_sheet(
            ws3,
            next_r3 + 1,
            ["Instrument", "Tenor", "Stop Rate (%)", "Bid-to-Cover", "Auction Date", "Source"],
            [
                [a.get("instrument"), a.get("tenor"), a.get("stop_rate_pct"), a.get("bid_to_cover"), a.get("auction_date"), a.get("source_url")]
                for a in auc_rows[:18]
            ],
        )
    _auto_fit_columns(ws3)

    # --------------------------------------------------------------------------
    # Sheet 4: 04_Macro_Indicators
    # --------------------------------------------------------------------------
    ws4 = wb.create_sheet("04_Macro_Indicators")
    ws4["A1"] = "Nigerian & Global Macroeconomic Indicators"
    ws4["A1"].font = TITLE_FONT
    macro_tbl = sections.get("section_04_macroeconomic_developments", {}).get("macro_table", [])
    macro_rows = [
        [
            m.get("indicator_code"),
            m.get("indicator_name"),
            m.get("country"),
            m.get("category"),
            m.get("latest_value"),
            m.get("previous_value"),
            m.get("change"),
            m.get("currency_or_unit"),
            m.get("reporting_period"),
        ]
        for m in macro_tbl
    ]
    _write_table_to_sheet(
        ws4,
        3,
        [
            "Indicator Code",
            "Indicator Name",
            "Country",
            "Category",
            "Latest Value",
            "Previous Value",
            "Change",
            "Unit",
            "Reporting Period",
        ],
        macro_rows,
    )
    _auto_fit_columns(ws4)

    # --------------------------------------------------------------------------
    # Sheet 5: 05_Equity_DCF_Valuations
    # --------------------------------------------------------------------------
    ws5 = wb.create_sheet("05_Equity_DCF_Valuations")
    ws5["A1"] = "NGX Covered Equities — Fundamental Ratios & 2-Stage DCF Valuations"
    ws5["A1"].font = TITLE_FONT
    eq_tbl = sections.get("section_07_equity_market_analysis", {}).get(
        "equity_valuation_table", []
    )
    eq_rows = [
        [
            e.get("ticker"),
            e.get("name"),
            e.get("sector"),
            e.get("current_price"),
            e.get("intrinsic_value_dcf"),
            e.get("upside_pct"),
            e.get("pe_ratio"),
            e.get("pb_ratio"),
            e.get("roe_pct"),
            e.get("dividend_yield_pct"),
            e.get("verdict"),
        ]
        for e in eq_tbl
    ]
    _write_table_to_sheet(
        ws5,
        3,
        [
            "Ticker",
            "Company Name",
            "Sector",
            "Share Price (NGN)",
            "2-Stage DCF Intrinsic Value",
            "Upside (%)",
            "P/E Ratio",
            "P/BV Ratio",
            "ROE (%)",
            "Dividend Yield (%)",
            "Valuation Verdict",
        ],
        eq_rows,
    )
    _auto_fit_columns(ws5)

    # --------------------------------------------------------------------------
    # Sheet 6: 06_Forecasts_And_Backtests
    # --------------------------------------------------------------------------
    ws6 = wb.create_sheet("06_Forecasts_And_Backtests")
    ws6["A1"] = "Walk-Forward Backtested Forecasts (Historical Strictly Separated from Forecasts)"
    ws6["A1"].font = TITLE_FONT
    fc_map = sections.get("section_13_risks_and_market_outlook", {}).get(
        "forecasts_and_backtests", {}
    )
    fc_rows = []
    for code, fc in fc_map.items():
        bt = fc.get("historical_backtest", {})
        fc_rows.append(
            [
                code,
                fc.get("target_name"),
                fc.get("model_family"),
                fc.get("forecast_horizon_label"),
                fc.get("last_historical_value"),
                fc.get("base_case"),
                fc.get("bull_case"),
                fc.get("bear_case"),
                fc.get("confidence_level_pct"),
                bt.get("rmse"),
                bt.get("mape_pct"),
                bt.get("directional_accuracy_pct"),
            ]
        )
    _write_table_to_sheet(
        ws6,
        3,
        [
            "Target Code",
            "Target Name",
            "Selected Model Family",
            "Horizon",
            "Last Historical Value",
            "Forecast Base Case",
            "Forecast Bull Case",
            "Forecast Bear Case",
            "Confidence (%)",
            "Backtest RMSE",
            "Backtest MAPE (%)",
            "Directional Accuracy (%)",
        ],
        fc_rows,
    )
    _auto_fit_columns(ws6)

    # --------------------------------------------------------------------------
    # Sheet 7: 07_Opportunity_Radar
    # --------------------------------------------------------------------------
    ws7 = wb.create_sheet("07_Opportunity_Radar")
    ws7["A1"] = "Investment & Strategic Business Opportunity Radar Rankings"
    ws7["A1"].font = TITLE_FONT
    inv_opps = sections.get("section_11_investment_opportunity_radar", {}).get(
        "approved_investment_opportunities", []
    )
    strat_opps = sections.get("section_12_strategic_business_opportunities", {}).get(
        "strategic_opportunities", []
    )
    opp_rows = [
        [
            o.get("opportunity_class"),
            o.get("radar_category"),
            o.get("target_business_line"),
            o.get("title"),
            o.get("instrument_or_sector"),
            o.get("composite_rank_score"),
            o.get("score_potential_return"),
            o.get("score_risk_adjusted"),
            o.get("score_evidence_quality"),
            o.get("time_horizon"),
            o.get("status"),
        ]
        for o in (inv_opps + strat_opps)
    ]
    _write_table_to_sheet(
        ws7,
        3,
        [
            "Opportunity Class",
            "Radar Category",
            "Target Business Line",
            "Opportunity Title",
            "Instrument / Sector",
            "Composite Score",
            "Return Score",
            "Risk-Adjusted Score",
            "Evidence Quality Score",
            "Time Horizon",
            "Status",
        ],
        opp_rows,
    )
    _auto_fit_columns(ws7)

    # --------------------------------------------------------------------------
    # Sheet 8: 08_Source_Register
    # --------------------------------------------------------------------------
    ws8 = wb.create_sheet("08_Source_Register")
    ws8["A1"] = "Traceable Institutional Source Register (Section 16)"
    ws8["A1"].font = TITLE_FONT
    sr_list = sections.get("section_16_references_and_source_register", {}).get(
        "source_register", []
    )
    sr_rows = [
        [
            s.get("id"),
            s.get("source_name"),
            s.get("publication_title"),
            s.get("publication_date"),
            s.get("reliability_classification"),
            s.get("epistemic_type"),
            s.get("url"),
            s.get("relevant_finding"),
        ]
        for s in sr_list
    ]
    _write_table_to_sheet(
        ws8,
        3,
        [
            "Citation UUID",
            "Source Name",
            "Publication Title",
            "Publication Date",
            "Reliability Classification",
            "Epistemic Type",
            "URL",
            "Relevant Verified Finding",
        ],
        sr_rows,
    )
    _auto_fit_columns(ws8)

    wb.save(str(output_path))
    logger.info("Generated OpenPyXL 8-sheet Excel workbook at %s", output_path)
    return output_path
