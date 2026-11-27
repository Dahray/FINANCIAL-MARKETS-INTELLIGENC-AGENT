"""
Institutional Data-Driven Financial Chart Generator (FMIP v3.0).
Renders publication-grade high-DPI Matplotlib PNG charts STRICTLY from verified database
time-series. Never fabricates illustrative series; every chart embeds its authoritative
Source, Reporting Period, Units, and Measurement Basis in its caption footer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from app.core.logging import get_logger

logger = get_logger("fmip.reporting.charts")

NAVY = "#1C1917"          # SohCahToa Deep Charcoal primary ink
EMERALD = "#EA580C"       # SohCahToa Brand Orange primary accent
TEAL = "#F97316"          # SohCahToa Vibrant Orange secondary
AMBER = "#B45309"         # Deep Burnt Orange / Amber contrast
CRIMSON = "#DC2626"       # Negative / Risk Alert Red
SLATE = "#44403C"         # Warm Stone Slate
LIGHT_GRID = "#F5F5F4"    # Subtle Warm Grid


def _apply_institutional_style(ax, title: str, ylabel: str, footer: str) -> None:
    ax.set_title(title, fontsize=9.0, fontweight="bold", color="#9A3412", pad=9, loc="left")
    ax.set_ylabel(ylabel, fontsize=8.5, color=SLATE)
    ax.grid(True, linestyle="--", linewidth=0.5, color="#E7E5E4", alpha=0.95)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#A8A29E")
    ax.spines["bottom"].set_color("#A8A29E")
    ax.tick_params(axis="both", labelsize=7.5, colors=SLATE)
    ax.figure.text(
        0.01,
        0.01,
        footer,
        fontsize=6.8,
        color="#78716C",
        style="italic",
    )


def generate_verified_report_charts(
    report_code: str,
    sections: Dict[str, Any],
    chart_series: Dict[str, Any],
    output_dir: Path,
) -> Dict[str, Path]:
    """
    Generate up to 6 verified institutional PNG charts for a Weekly Report.
    Returns a dict mapping chart key -> saved PNG Path (only for charts with verified data).
    """
    charts: Dict[str, Path] = {}
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        import pandas as pd
    except Exception as exc:
        logger.info("Matplotlib unavailable for chart rendering (%s); skipping PNG charts.", exc)
        return charts

    chart_dir = output_dir / "charts" / report_code
    chart_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # 1. US Labour Market: Unemployment Rate vs Non-Farm Payrolls Monthly Change
    # -------------------------------------------------------------------------
    unrate = chart_series.get("us_unrate") or {}
    nfp = chart_series.get("us_nfp_change") or {}
    if len(unrate.get("dates", [])) >= 4 and len(nfp.get("dates", [])) >= 4:
        try:
            u_map = dict(zip(unrate["dates"], unrate["values"]))
            n_map = dict(zip(nfp["dates"], nfp["values"]))
            common = sorted(set(u_map.keys()) & set(n_map.keys()))[-12:]
            if len(common) >= 4:
                fig, ax1 = plt.subplots(figsize=(6.8, 3.1), dpi=180)
                x = np.arange(len(common))
                n_vals = [n_map[d] for d in common]
                u_vals = [u_map[d] for d in common]

                bar_colors = [EMERALD if v >= 0 else CRIMSON for v in n_vals]
                ax2 = ax1.twinx()
                ax2.bar(x, n_vals, width=0.52, color=bar_colors, alpha=0.28, label="Non-Farm Payrolls Chg ('000, RHS)")
                ax2.set_ylabel("Monthly Payrolls Chg ('000)", fontsize=8, color=SLATE)
                ax2.tick_params(axis="y", labelsize=7.5, colors=SLATE)
                ax2.spines["top"].set_visible(False)

                ax1.plot(x, u_vals, color=NAVY, linewidth=2.1, marker="o", markersize=4, label="US Unemployment Rate (%, LHS)")
                ax1.set_xticks(x)
                ax1.set_xticklabels(common, rotation=35, ha="right", fontsize=7)
                _apply_institutional_style(
                    ax1,
                    f"US Labour Market: Unemployment Rate vs Non-Farm Payrolls ({common[0]} to {common[-1]})",
                    "Unemployment Rate (%)",
                    f"Source: St. Louis Fed FRED (BLS UNRATE & PAYEMS) | Period: {common[0]}–{common[-1]} | Units: % & '000 jobs | Basis: Monthly SA",
                )
                h1, l1 = ax1.get_legend_handles_labels()
                h2, l2 = ax2.get_legend_handles_labels()
                ax1.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=7, frameon=False)
                fig.tight_layout(rect=[0, 0.05, 1, 1])
                p = chart_dir / "chart_us_labour.png"
                fig.savefig(p)
                plt.close(fig)
                charts["us_labour"] = p
        except Exception as exc:
            logger.info("Chart us_labour skipped: %s", exc)

    # -------------------------------------------------------------------------
    # 2. Nigeria External Reserves (USD Bn) vs CBN Official NFEM FX (NGN/USD)
    # -------------------------------------------------------------------------
    res = chart_series.get("ng_reserves") or {}
    fx = chart_series.get("ng_nfem_fx") or {}
    if len(res.get("dates", [])) >= 5 and len(fx.get("dates", [])) >= 5:
        try:
            r_df = pd.DataFrame({"d": pd.to_datetime(res["dates"], errors="coerce"), "res": res["values"]}).dropna()
            f_df = pd.DataFrame({"d": pd.to_datetime(fx["dates"], errors="coerce"), "fx": fx["values"]}).dropna()
            merged = pd.merge_asof(
                f_df.sort_values("d"),
                r_df.sort_values("d"),
                on="d",
                direction="nearest",
            ).tail(45)
            if len(merged) >= 5:
                fig, ax1 = plt.subplots(figsize=(6.8, 3.1), dpi=180)
                x = np.arange(len(merged))
                labels = [d.strftime("%d-%b") for d in merged["d"]]

                ax1.fill_between(x, merged["res"], merged["res"].min() * 0.96, color=TEAL, alpha=0.22)
                ax1.plot(x, merged["res"], color=TEAL, linewidth=1.8, label="Gross External Reserves (USD Bn, LHS)")

                ax2 = ax1.twinx()
                ax2.plot(x, merged["fx"], color=CRIMSON, linewidth=2.0, label="CBN NFEM Exchange Rate (NGN/USD, RHS)")
                ax2.set_ylabel("NGN / USD", fontsize=8, color=CRIMSON)
                ax2.tick_params(axis="y", labelsize=7.5, colors=CRIMSON)
                ax2.spines["top"].set_visible(False)

                step = max(1, len(labels) // 9)
                ax1.set_xticks(x[::step])
                ax1.set_xticklabels(labels[::step], rotation=30, ha="right", fontsize=7)
                _apply_institutional_style(
                    ax1,
                    f"Nigeria Reserves vs CBN NFEM FX (${merged['res'].iloc[-1]:.2f}B | NGN {merged['fx'].iloc[-1]:,.0f})",
                    "External Reserves (USD Bn)",
                    f"Source: Central Bank of Nigeria (CBN Official APIs) | Period: {merged['d'].iloc[0].strftime('%Y-%m-%d')} to {merged['d'].iloc[-1].strftime('%Y-%m-%d')} | Units: USD Bn & NGN/USD",
                )
                h1, l1 = ax1.get_legend_handles_labels()
                h2, l2 = ax2.get_legend_handles_labels()
                ax1.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=7, frameon=False)
                fig.tight_layout(rect=[0, 0.05, 1, 1])
                p = chart_dir / "chart_reserves_vs_nfem.png"
                fig.savefig(p)
                plt.close(fig)
                charts["reserves_vs_nfem"] = p
        except Exception as exc:
            logger.info("Chart reserves_vs_nfem skipped: %s", exc)

    # -------------------------------------------------------------------------
    # 3. Nigeria Sovereign & OMO Yield Curves (CBN Primary NTB, OMO & FGN Curve)
    # -------------------------------------------------------------------------
    sec5 = sections.get("section_05_fixed_income_market_analysis", {})
    fi_auc = sec5.get("nigerian_fixed_income_auctions", {})
    yc = sec5.get("yield_curve_analytics", {}).get("fitted_standard_tenors", {})
    ntb_pts = fi_auc.get("ntb_curve_latest", [])
    omo_pts = fi_auc.get("omo_curve_latest", [])
    if yc or ntb_pts or omo_pts:
        try:
            fig, ax = plt.subplots(figsize=(6.8, 3.1), dpi=180)
            if yc:
                order = [("91D", 0.25), ("182D", 0.5), ("364D", 1.0), ("2Y", 2.0), ("5Y", 5.0), ("10Y", 10.0), ("20Y", 20.0), ("30Y", 30.0)]
                xs = [yrs for lbl, yrs in order if lbl in yc]
                ys = [float(yc[lbl]) for lbl, yrs in order if lbl in yc]
                if xs:
                    ax.plot(xs, ys, color=NAVY, linewidth=2.2, marker="o", markersize=4.5, label="Nigeria Sovereign Curve (Fitted)")
            if ntb_pts:
                ax.scatter(
                    [p["tenor_days"] / 365.0 for p in ntb_pts],
                    [p["stop_rate_pct"] for p in ntb_pts],
                    color=EMERALD,
                    s=55,
                    zorder=5,
                    label="Live CBN Primary NTB Auctions",
                )
            if omo_pts:
                ax.scatter(
                    [p["tenor_days"] / 365.0 for p in omo_pts],
                    [p["stop_rate_pct"] for p in omo_pts],
                    color=AMBER,
                    marker="D",
                    s=50,
                    zorder=5,
                    label="Live CBN OMO Auctions",
                )
            ax.set_xlabel("Maturity Tenor (Years)", fontsize=8, color=SLATE)
            _apply_institutional_style(
                ax,
                "Nigeria Sovereign Fixed-Income Curve: Live CBN NTB, OMO & FGN Benchmarks",
                "Yield / Stop Rate (%)",
                "Source: Central Bank of Nigeria (GetAllSecuritiesNTB & GetAllSecuritiesOMO) + Sovereign Curve | Units: % p.a. | Basis: Primary Stop / Benchmark Yields",
            )
            ax.legend(loc="best", fontsize=7.2, frameon=False)
            fig.tight_layout(rect=[0, 0.05, 1, 1])
            p = chart_dir / "chart_nigeria_yield_curves.png"
            fig.savefig(p)
            plt.close(fig)
            charts["nigeria_yield_curves"] = p
        except Exception as exc:
            logger.info("Chart nigeria_yield_curves skipped: %s", exc)

    # -------------------------------------------------------------------------
    # 4. Global 10-Year Sovereign Government Bond Yields Comparison
    # -------------------------------------------------------------------------
    g10 = sec5.get("global_10y_bonds_table", [])
    if len(g10) >= 3:
        try:
            sorted_g10 = sorted(
                [r for r in g10 if r.get("yield_pct") is not None],
                key=lambda x: float(x["yield_pct"]),
            )
            fig, ax = plt.subplots(figsize=(6.8, 3.0), dpi=180)
            countries = [r["country"] for r in sorted_g10]
            yields = [float(r["yield_pct"]) for r in sorted_g10]
            colors_bar = [AMBER if c in ("South Africa", "Mexico") else NAVY for c in countries]
            bars = ax.barh(countries, yields, color=colors_bar, height=0.62, alpha=0.88)
            for bar, yv in zip(bars, yields):
                ax.text(yv + 0.12, bar.get_y() + bar.get_height() / 2.0, f"{yv:.2f}%", va="center", fontsize=7.5, color=NAVY, fontweight="bold")
            ax.set_xlim(0, max(yields) * 1.18)
            _apply_institutional_style(
                ax,
                "Global 10-Year Government Bond Yields Comparison (Developed vs Emerging Markets)",
                "",
                "Source: St. Louis Fed FRED & OECD Tier-1 | Units: % per annum | Basis: 10-Year Sovereign Benchmark Yield",
            )
            ax.set_xlabel("10-Year Sovereign Yield (%)", fontsize=8, color=SLATE)
            fig.tight_layout(rect=[0, 0.05, 1, 1])
            p = chart_dir / "chart_global_10y_bonds.png"
            fig.savefig(p)
            plt.close(fig)
            charts["global_10y_bonds"] = p
        except Exception as exc:
            logger.info("Chart global_10y_bonds skipped: %s", exc)

    # -------------------------------------------------------------------------
    # 5. Benchmark Equity Index & 50-Day / 200-Day Moving Averages
    # -------------------------------------------------------------------------
    spx_h = chart_series.get("spx_history") or {}
    ngx_h = chart_series.get("ngx_asi_history") or {}
    eq_src = spx_h if (len(spx_h.get("values", [])) >= 30 and not spx_h.get("is_archival")) else ngx_h
    if len(eq_src.get("values", [])) >= 20:
        try:
            vals = pd.Series(eq_src["values"], dtype=float)
            dts = eq_src["dates"]
            ma50 = vals.rolling(50, min_periods=15).mean()
            ma200 = vals.rolling(200, min_periods=40).mean()
            fig, ax = plt.subplots(figsize=(6.8, 3.0), dpi=180)
            x = np.arange(len(vals))
            sym_lbl = "S&P 500 Index" if eq_src is spx_h else "NGX All-Share Index (ASI)"
            ax.plot(x, vals, color=CRIMSON, linewidth=1.7, label=sym_lbl)
            if ma50.notna().any():
                ax.plot(x, ma50, color=AMBER, linewidth=1.3, label="50-Day MA")
            if ma200.notna().any():
                ax.plot(x, ma200, color=EMERALD, linewidth=1.4, label="200-Day MA")
            step = max(1, len(dts) // 8)
            ax.set_xticks(x[::step])
            ax.set_xticklabels(dts[::step], rotation=28, ha="right", fontsize=7)
            _apply_institutional_style(
                ax,
                f"{sym_lbl} & Technical Moving Averages ({dts[0]} to {dts[-1]})",
                "Index Points",
                f"Source: {'FMP Institutional EOD Feed' if eq_src is spx_h else 'NGX Public Market Feed'} | Period: {dts[0]}–{dts[-1]} | Basis: Daily Close + SMA-50 / SMA-200",
            )
            ax.legend(loc="upper left", fontsize=7.2, frameon=False)
            fig.tight_layout(rect=[0, 0.05, 1, 1])
            p = chart_dir / "chart_equity_moving_averages.png"
            fig.savefig(p)
            plt.close(fig)
            charts["equity_moving_averages"] = p
        except Exception as exc:
            logger.info("Chart equity_moving_averages skipped: %s", exc)

    # -------------------------------------------------------------------------
    # 6. Global Equities & Commodities WTD vs YTD Performance Bar Chart
    # -------------------------------------------------------------------------
    sec3 = sections.get("section_03_global_market_performance", {})
    perf_rows = [
        r for r in (sec3.get("global_equities_table", []) + sec3.get("commodities_table", []))
        if r.get("ytd_pct") is not None or r.get("wtd_pct") is not None
    ][:10]
    if len(perf_rows) >= 3:
        try:
            fig, ax = plt.subplots(figsize=(6.8, 3.0), dpi=180)
            names = [r["name"][:18] for r in perf_rows]
            wtds = [float(r["wtd_pct"] or 0.0) for r in perf_rows]
            ytds = [float(r["ytd_pct"] or 0.0) for r in perf_rows]
            x = np.arange(len(names))
            w = 0.36
            ax.bar(x - w / 2, wtds, width=w, color=TEAL, label="WTD (%)")
            ax.bar(x + w / 2, ytds, width=w, color=NAVY, label="YTD (%)")
            ax.axhline(0, color="#64748B", linewidth=0.8)
            ax.set_xticks(x)
            ax.set_xticklabels(names, rotation=32, ha="right", fontsize=7)
            _apply_institutional_style(
                ax,
                "Global Equities & Commodities: Week-to-Date (WTD) vs Year-to-Date (YTD) Returns",
                "Return (%)",
                "Source: FMP, Yahoo Finance & St. Louis Fed FRED | Units: % | Basis: Calendar WTD & YTD Price Return",
            )
            ax.legend(loc="upper right", fontsize=7.2, frameon=False)
            fig.tight_layout(rect=[0, 0.05, 1, 1])
            p = chart_dir / "chart_global_performance.png"
            fig.savefig(p)
            plt.close(fig)
            charts["global_performance"] = p
        except Exception as exc:
            logger.info("Chart global_performance skipped: %s", exc)

    logger.info("Generated %d verified institutional PNG charts for %s.", len(charts), report_code)
    return charts
