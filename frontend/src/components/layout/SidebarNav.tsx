"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  Bot,
  Building2,
  Compass,
  FileSpreadsheet,
  Globe2,
  Scale,
  Settings,
  ShieldCheck,
} from "lucide-react";

const NAV_ITEMS = [
  {
    name: "1. Executive Overview",
    href: "/overview",
    icon: Activity,
    subtitle: "5 Strategic Questions & Pulse",
  },
  {
    name: "2. Nigerian Markets",
    href: "/nigerian-markets",
    icon: BarChart3,
    subtitle: "NGX, FMDQ, NTB, Bonds & FX",
  },
  {
    name: "3. Global Markets",
    href: "/global-markets",
    icon: Globe2,
    subtitle: "Equities, UST, FX & Commodities",
  },
  {
    name: "4. Opportunity Radar",
    href: "/opportunity-radar",
    icon: Compass,
    subtitle: "Investment & Business Theses",
  },
  {
    name: "5. Competitive Intel",
    href: "/competitive-intelligence",
    icon: Building2,
    subtitle: "9 Industry Segments & Moves",
  },
  {
    name: "6. Regulatory Monitor",
    href: "/regulatory-monitor",
    icon: Scale,
    subtitle: "CBN, SEC, PenCom & Citations",
  },
  {
    name: "7. Research Reports",
    href: "/research-reports",
    icon: FileSpreadsheet,
    subtitle: "16-Section Friday Reports",
  },
  {
    name: "8. AI Research Assistant",
    href: "/ai-assistant",
    icon: Bot,
    subtitle: "Citation-Backed Executive Q&A",
  },
  {
    name: "Automation & Settings",
    href: "/settings",
    icon: Settings,
    subtitle: "n8n, Alerts & Data Providers",
  },
];

export function SidebarNav() {
  const pathname = usePathname();

  return (
    <aside className="w-72 shrink-0 border-r border-slate-800/90 bg-slate-950/95 flex flex-col justify-between min-h-screen">
      <div>
        {/* Brand Header */}
        <div className="border-b border-slate-800/90 px-5 py-5">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-500/15 border border-emerald-500/40 text-emerald-400 font-bold font-mono">
              FM
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-wide text-white uppercase">
                SohCahToa FMIP
              </h1>
              <p className="text-[11px] text-emerald-400 font-mono">
                Institutional Intelligence Desk
              </p>
            </div>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="p-3 space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active =
              pathname === item.href ||
              (item.href !== "/overview" && pathname?.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-start gap-3 rounded-lg px-3 py-2.5 transition-all ${
                  active
                    ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 shadow-sm"
                    : "text-slate-300 hover:bg-slate-900 hover:text-white border border-transparent"
                }`}
              >
                <Icon
                  className={`h-4 w-4 mt-0.5 shrink-0 ${
                    active ? "text-emerald-400" : "text-slate-400"
                  }`}
                />
                <div>
                  <div className="text-xs font-semibold">{item.name}</div>
                  <div className="text-[11px] text-slate-400">{item.subtitle}</div>
                </div>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Institutional Governance Footer */}
      <div className="border-t border-slate-800/90 p-4 space-y-2.5 bg-slate-900/40">
        <div className="flex items-center gap-2 text-xs text-emerald-400 font-medium">
          <ShieldCheck className="h-4 w-4 shrink-0" />
          <span>Chief Editor Quality Gate Active</span>
        </div>
        <p className="text-[11px] text-slate-400 leading-relaxed">
          All numerical metrics are computed by Agent 6 (Python Quant Engine). Decision-support system only; no automated trade execution.
        </p>
        <div className="pt-1 flex items-center justify-between text-[11px] font-mono text-slate-500">
          <span>RBAC: EXECUTIVE_ADMIN</span>
          <Link href="/login" className="text-sky-400 hover:underline">
            Session
          </Link>
        </div>
      </div>
    </aside>
  );
}
