"use client";

import React, { useEffect, useState } from "react";
import {
  Briefcase,
  Database,
  FileClock,
  Search,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { fmipApi } from "@/lib/api";
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/primitives";

export default function ResearchMemoryPage() {
  const [query, setQuery] = useState("");
  const [lookback, setLookback] = useState("ALL");
  const [memory, setMemory] = useState<any>(null);
  const [selectedTab, setSelectedTab] = useState<
    "CHANGE_LOG" | "FINDINGS" | "RECOMMENDATIONS" | "RISKS" | "REPORTS"
  >("CHANGE_LOG");

  const loadMemory = async (q = query, lb = lookback) => {
    try {
      const res = await fmipApi.getResearchMemory(q, lb);
      setMemory(res);
    } catch {}
  };

  useEffect(() => {
    loadMemory("", "ALL");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadMemory(query, lookback);
  };

  const changeLog: any[] = memory?.intelligence_change_log || [];
  const findings: any[] = memory?.research_findings || [];
  const recs: any[] = memory?.strategic_recommendations || [];
  const risks: any[] = memory?.identified_risks || [];
  const reports: any[] = memory?.reports || [];
  const qaScorecard: Record<string, number> = memory?.qa_scorecard || {};

  return (
    <div className="space-y-6">
      <div>
        <Badge variant="sky">PART 2, 5C & 5E: INSTITUTIONAL RESEARCH MEMORY & AUDIT LOG</Badge>
        <h1 className="mt-1 text-2xl font-bold text-white">
          Searchable Historical Research Memory, 14-Point Business Cases & Change Log
        </h1>
        <p className="text-xs text-slate-400">
          Search persistent findings tracked across weeks, strategic recommendations with 14-point business cases, active risk registers, 9-dimension QA scorecards, and every audited data correction.
        </p>
      </div>

      {/* Search & Horizon Filter Bar */}
      <form onSubmit={handleSearch} className="flex flex-wrap items-center gap-3 text-xs">
        <div className="relative flex-1 min-w-[260px]">
          <Search className="h-4 w-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search historical reports, MPR corrections, findings, recommendations, risks..."
            className="w-full rounded-lg border border-slate-700 bg-slate-900 pl-9 pr-3 py-2 text-white"
          />
        </div>
        <select
          value={lookback}
          onChange={(e) => {
            setLookback(e.target.value);
            loadMemory(query, e.target.value);
          }}
          className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white font-mono"
        >
          <option value="ALL">All History</option>
          <option value="1W">Previous Week (1W)</option>
          <option value="1M">Previous Month (1M)</option>
          <option value="3M">Previous Quarter (3M)</option>
          <option value="6M">Previous 6 Months (6M)</option>
          <option value="1Y">Previous Year (1Y)</option>
        </select>
        <button
          type="submit"
          className="rounded-lg bg-emerald-600 hover:bg-emerald-500 px-4 py-2 font-semibold text-white"
        >
          Search Memory
        </button>
      </form>

      {/* 9-Dimension Research Quality Assurance Scorecard (Vision #5) */}
      {Object.keys(qaScorecard).length > 0 && (
        <Card className="border-emerald-800/50">
          <CardHeader className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-emerald-400" />
              <CardTitle>Independent Research Quality Assurance Scorecard (9 Dimensions)</CardTitle>
            </div>
            <Badge variant="emerald">CHIEF RESEARCH EDITOR QA</Badge>
          </CardHeader>
          <CardContent className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5 text-xs">
            {Object.entries(qaScorecard).map(([k, v]) => (
              <div key={k} className="rounded border border-slate-800 bg-slate-950/70 p-2.5">
                <div className="text-[10px] uppercase text-slate-400 truncate">
                  {k.replace(/^\d+_/, "").replace(/_/g, " ")}
                </div>
                <div className="mt-1 font-mono text-base font-bold text-emerald-300">
                  {v}%
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Navigation Tabs */}
      <div className="flex flex-wrap gap-2 text-xs">
        {[
          { key: "CHANGE_LOG", label: `Intelligence Change Log (${changeLog.length})`, icon: FileClock },
          { key: "FINDINGS", label: `Tracked Findings (${findings.length})`, icon: Database },
          { key: "RECOMMENDATIONS", label: `Strategic Recs & 14-Pt Cases (${recs.length})`, icon: Briefcase },
          { key: "RISKS", label: `Risk Register (${risks.length})`, icon: ShieldAlert },
          { key: "REPORTS", label: `Historical Reports (${reports.length})`, icon: FileClock },
        ].map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.key}
              onClick={() => setSelectedTab(tab.key as any)}
              className={`flex items-center gap-1.5 rounded-lg px-3.5 py-2 font-semibold transition-colors ${
                selectedTab === tab.key
                  ? "bg-sky-600 text-white"
                  : "border border-slate-800 bg-slate-900 text-slate-300 hover:bg-slate-800"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      {selectedTab === "CHANGE_LOG" && (
        <Card>
          <CardHeader>
            <CardTitle>Part 5E: Immutable Intelligence & Data Correction Change Log</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2.5 text-xs">
            {changeLog.map((c) => (
              <div key={c.id} className="rounded-lg border border-slate-800 bg-slate-950/70 p-3 space-y-1">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Badge variant={c.change_category === "DATA_CORRECTION" ? "amber" : "sky"}>
                      {c.change_category}
                    </Badge>
                    <span className="font-mono text-white font-semibold">{c.entity_id}</span>
                  </div>
                  <span className="font-mono text-[10px] text-slate-400">{c.created_at} • {c.source_or_actor}</span>
                </div>
                <p className="text-slate-300">{c.summary}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {selectedTab === "FINDINGS" && (
        <Card>
          <CardHeader>
            <CardTitle>Persistent Research Findings Tracked Across Reporting Periods</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            {findings.map((f) => (
              <div key={f.finding_code} className="rounded-lg border border-slate-800 bg-slate-950/70 p-3.5 space-y-1.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sky-400 font-bold">{f.finding_code}</span>
                    <Badge variant="emerald">{f.status}</Badge>
                    <Badge variant="slate">{f.domain}</Badge>
                  </div>
                  <span className="font-mono text-[10px] text-slate-400">
                    First: {f.first_report_code} • Latest: {f.last_report_code}
                  </span>
                </div>
                <div className="font-semibold text-white">{f.title}</div>
                <p className="text-slate-300">{f.summary}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {selectedTab === "RECOMMENDATIONS" && (
        <Card>
          <CardHeader>
            <CardTitle>Tracked Strategic Recommendations & 14-Point Preliminary Business Cases</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-xs">
            {recs.map((r) => (
              <div key={r.recommendation_code} className="rounded-lg border border-slate-800 bg-slate-950/70 p-4 space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-emerald-400">{r.recommendation_code}</span>
                    <Badge variant="emerald">{r.status}</Badge>
                    <Badge variant="sky">{r.target_business_line}</Badge>
                  </div>
                  <span className="font-mono text-[10px] text-amber-400">Review Date: {r.review_date}</span>
                </div>
                <div className="font-bold text-white text-sm">{r.title}</div>
                <p className="text-slate-300">{r.original_recommendation}</p>
                {r.preliminary_business_case && Object.keys(r.preliminary_business_case).length > 0 && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-2 border-t border-slate-800 text-[11px]">
                    <div><strong className="text-sky-400">Market Size:</strong> <span className="text-slate-300">{r.preliminary_business_case["2_market_size"]}</span></div>
                    <div><strong className="text-sky-400">Revenue Model:</strong> <span className="text-slate-300">{r.preliminary_business_case["7_revenue_model"]}</span></div>
                    <div><strong className="text-sky-400">Regulatory:</strong> <span className="text-slate-300">{r.preliminary_business_case["6_regulatory_requirements"]}</span></div>
                    <div><strong className="text-sky-400">Profitability:</strong> <span className="text-slate-300">{r.preliminary_business_case["10_potential_profitability"]}</span></div>
                  </div>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {selectedTab === "RISKS" && (
        <Card>
          <CardHeader>
            <CardTitle>Persistent Institutional Risk Register</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            {risks.map((rk) => (
              <div key={rk.risk_code} className="rounded-lg border border-rose-900/40 bg-slate-950/70 p-3.5 space-y-1.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-rose-400">{rk.risk_code}</span>
                    <Badge variant="rose">{rk.severity} SEVERITY</Badge>
                    <Badge variant="amber">{rk.status}</Badge>
                  </div>
                  <span className="font-mono text-[10px] text-slate-400">Trigger: {rk.trigger_indicator_code} ({rk.trigger_threshold})</span>
                </div>
                <div className="font-semibold text-white">{rk.title}</div>
                <p className="text-slate-300">{rk.description}</p>
                <p className="text-[11px] text-emerald-300"><strong>Mitigation:</strong> {rk.mitigation_strategy}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {selectedTab === "REPORTS" && (
        <Card>
          <CardHeader>
            <CardTitle>Historical Weekly Intelligence Reports Archive</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            {reports.map((rp) => (
              <div key={rp.report_code} className="rounded-lg border border-slate-800 bg-slate-950/70 p-3.5 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-emerald-400">{rp.report_code}</span>
                  <span className="font-mono text-[10px] text-slate-400">{rp.period_start} → {rp.period_end}</span>
                </div>
                <div className="font-semibold text-white">{rp.title}</div>
                <p className="text-slate-300">{rp.executive_summary}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
