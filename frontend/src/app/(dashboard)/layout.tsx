"use client";

import React from "react";
import { SidebarNav } from "@/components/layout/SidebarNav";

const LIVE_TICKER_ITEMS = [
  { label: "NGX ASI", value: "101,350.85", change: "+0.67% WoW", positive: true },
  { label: "NAFEM USD/NGN", value: "1,668.90", change: "-0.65% WoW (NGN Firm)", positive: true },
  { label: "364D NTB YIELD", value: "22.85%", change: "Peak Front-End Carry", positive: true },
  { label: "10Y FGN BOND", value: "20.30%", change: "Mod Dur 4.18Y", positive: true },
  { label: "HEADLINE CPI", value: "33.88%", change: "Food CPI 39.16%", positive: false },
  { label: "CBN MPR / CRR", value: "27.50% / 50%", change: "Hawkish Hold", positive: true },
  { label: "FX RESERVES", value: "$40.28B", change: "~11m Import Cover", positive: true },
  { label: "BONNY LIGHT", value: "$83.95/bbl", change: "Brent $82.10", positive: true },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <SidebarNav />
      <div className="flex-1 flex flex-col min-w-0">
        {/* Institutional Market Ticker Bar */}
        <header className="border-b border-slate-800/90 bg-slate-900/90 px-6 py-2.5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-5 text-xs">
              {LIVE_TICKER_ITEMS.map((item) => (
                <div key={item.label} className="flex items-center gap-1.5">
                  <span className="font-semibold text-slate-400">{item.label}:</span>
                  <span className="font-mono font-bold text-white">{item.value}</span>
                  <span
                    className={`font-mono text-[11px] ${
                      item.positive ? "text-emerald-400" : "text-amber-400"
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
