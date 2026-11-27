"use client";

import React, { useEffect, useState } from "react";
import { SidebarNav } from "@/components/layout/SidebarNav";
import { fmipApi } from "@/lib/api";

interface TickerItem {
  label: string;
  value: string;
  change: string;
  positive: boolean;
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [tickerItems, setTickerItems] = useState<TickerItem[]>([
    { label: "CBN MPR", value: "Loading...", change: "Tier-1 CBN", positive: true },
    { label: "HEADLINE CPI", value: "Loading...", change: "Tier-1 CBN", positive: true },
    { label: "NFEM USD/NGN", value: "Loading...", change: "Official FX", positive: true },
    { label: "FX RESERVES", value: "Loading...", change: "Tier-1 CBN", positive: true },
  ]);

  useEffect(() => {
    let active = true;
    fmipApi
      .getOverviewDashboard()
      .then((res) => {
        if (!active || !res) return;
        const macro = res.macro_snapshot || {};
        const mkt = res.market_metrics || {};
        const yc = res.fixed_income_summary?.yield_curve?.fitted_standard_tenors || {};

        const mpr = macro["NG_CBN_MPR"];
        const cpi = macro["NG_CPI_HEADLINE_YOY"];
        const resv = macro["NG_FX_RESERVES_USD"];
        const fx = mkt["NGNUSD.NAFEM"];
        const brent = mkt["BRENT"];
        const bonny = mkt["BONNYLIGHT"];
        const spx = mkt["SPX"];

        const fmt = (v: any, d = 2, suf = "") =>
          typeof v === "number" && !Number.isNaN(v)
            ? `${v.toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d })}${suf}`
            : "—";

        setTickerItems([
          {
            label: "CBN MPR",
            value: fmt(mpr?.latest_value, 2, "%"),
            change: mpr?.reporting_period || "CBN Live",
            positive: true,
          },
          {
            label: "HEADLINE CPI",
            value: fmt(cpi?.latest_value, 2, "%"),
            change: cpi?.reporting_period || "YoY",
            positive: true,
          },
          {
            label: "NFEM USD/NGN",
            value: fmt(fx?.latest_price, 2),
            change: "CBN Official",
            positive: true,
          },
          {
            label: "FX RESERVES",
            value: `$${fmt(resv?.latest_value, 2, "B")}`,
            change: "Gross USD",
            positive: true,
          },
          {
            label: "364D NTB",
            value: fmt(yc["364D"] ?? yc["1Y"], 2, "%"),
            change: "Primary Stop",
            positive: true,
          },
          {
            label: "BONNY / BRENT",
            value: `$${fmt(bonny?.latest_price, 2)} / $${fmt(brent?.latest_price, 2)}`,
            change: "Crude Oil",
            positive: true,
          },
          {
            label: "S&P 500",
            value: fmt(spx?.latest_price, 2),
            change: "Global Equity",
            positive: (spx?.period_returns_pct?.["1W"] ?? 0) >= 0,
          },
        ]);
      })
      .catch(() => {
        // Keep loading placeholder if backend offline
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="flex min-h-screen bg-stone-950 text-stone-100">
      <SidebarNav />
      <div className="flex-1 flex flex-col min-w-0">
        {/* SohCahToa Orange Top Institutional Live Market Ticker Bar */}
        <header className="border-b-2 border-orange-600/80 bg-stone-900/95 px-6 py-2.5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-5 text-xs">
              {tickerItems.map((item) => (
                <div key={item.label} className="flex items-center gap-1.5">
                  <span className="font-semibold text-orange-400">{item.label}:</span>
                  <span className="font-mono font-bold text-white">{item.value}</span>
                  <span
                    className={`font-mono text-[11px] ${
                      item.positive ? "text-stone-400" : "text-rose-400"
                    }`}
                  >
                    ({item.change})
                  </span>
                </div>
              ))}
            </div>
          </div>
        </header>

        {/* Main Page Content */}
        <main className="flex-1 p-6 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
