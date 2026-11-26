"use client";

import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  ExternalLink,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { fmipApi } from "@/lib/api";
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  MetricStatCard,
} from "@/components/ui/primitives";

export default function DataAccuracyMonitorPage() {
  const [monitor, setMonitor] = useState<any>(null);
  const [auditing, setAuditing] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string>("ALL");
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const loadMonitor = async () => {
    try {
      const res = await fmipApi.getDataAccuracyMonitor();
      setMonitor(res);
    } catch {
      // backend offline
    }
  };

  useEffect(() => {
    loadMonitor();
  }, []);

  const handleRunAudit = async () => {
    setAuditing(true);
    setStatusMsg(null);
    try {
      const res = await fmipApi.runLiveVerificationAudit(true);
      if (res?.accuracy_monitor) {
        setMonitor(res.accuracy_monitor);
      } else {
        await loadMonitor();
      }
      setStatusMsg(
        "Live official CBN/FRED/Market verification & cross-source discrepancy audit completed."
      );
    } catch {
      setStatusMsg("Verification audit could not reach live backend.");
    } finally {
      setAuditing(false);
    }
  };

  const summary = monitor?.summary || {};
  const indicators: any[] = monitor?.indicators || [];
  const discrepancies: any[] = monitor?.discrepancies || [];

  const filtered = indicators.filter((item) => {
    if (filterStatus === "ALL") return true;
    if (filterStatus === "FRESH") return item.freshness_status === "FRESH";
    if (filterStatus === "ATTENTION")
      return item.freshness_status !== "FRESH";
    return item.domain === filterStatus;
  });

  const freshnessBadgeVariant = (status: string) => {
    if (status === "FRESH") return "emerald";
    if (status === "AGING") return "amber";
    return "rose";
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <Badge variant="emerald">PART 1 & 5A: SOURCE-OF-TRUTH GOVERNANCE</Badge>
          <h1 className="mt-1 text-2xl font-bold text-white">
            Financial Data Accuracy, Freshness SLA & Discrepancy Monitor
          </h1>
          <p className="text-xs text-slate-400">
            Tier 1 Official Primary Sources (CBN, NGX, FMDQ, DMO, NBS, FRED) &gt; Tier 2 Providers (FMP, Alpha Vantage) &gt; Tier 3 Financial Press. Never silently presents stale or archival data as live.
          </p>
        </div>

        <button
          onClick={handleRunAudit}
          disabled={auditing}
          className="flex items-center gap-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 px-4 py-2 text-xs font-semibold text-white shadow"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${auditing ? "animate-spin" : ""}`} />
          {auditing ? "Auditing Live CBN & Market Feeds..." : "Run Live Official Verification Audit"}
        </button>
      </div>

      {statusMsg && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-700/60 bg-emerald-950/50 p-3 text-xs text-emerald-300">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>{statusMsg}</span>
        </div>
      )}

      {/* Top Governance KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricStatCard
          label="Live Verified & Fresh Indicators"
          value={`${summary.live_verified_fresh ?? "—"} / ${summary.total_tracked_indicators ?? "—"}`}
          unit="LIVE"
          subValue={`Accuracy Score: ${summary.data_accuracy_score_pct ?? 0}% Live Fresh`}
          badgeText="TIER-1/2"
        />
        <MetricStatCard
          label="Stale / Archival Warnings"
          value={String(summary.stale_or_archival_count ?? "—")}
          unit="FLAGGED"
          subValue="Explicitly labeled — never shown as current"
          badgeText="SLA GUARD"
        />
        <MetricStatCard
          label="Cross-Source Discrepancies Audited"
          value={String(summary.discrepancies_logged ?? "—")}
          unit="RECORDS"
          subValue="Resolved by Tier 1 > Tier 2 > Archival hierarchy"
          badgeText="AUDIT TRAIL"
        />
        <MetricStatCard
          label="Unresolved Disputed Figures"
          value={String(summary.disputed_count ?? 0)}
          unit="OPEN"
          subValue={`Last Audited: ${monitor?.audited_at_utc ? monitor.audited_at_utc.slice(0, 19).replace("T", " ") + " UTC" : "—"}`}
          badgeText="GOVERNANCE"
        />
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        {[
          { key: "ALL", label: `All Indicators (${indicators.length})` },
          { key: "FRESH", label: `Live Verified & Fresh (${summary.live_verified_fresh ?? 0})` },
          { key: "ATTENTION", label: `Stale / Archival / Attention (${(summary.aging_count || 0) + (summary.stale_or_archival_count || 0) + (summary.disputed_count || 0)})` },
          { key: "MACROECONOMIC", label: "Macroeconomic" },
          { key: "MARKET", label: "Markets & FX" },
          { key: "FIXED_INCOME_YIELD", label: "Sovereign Yield Curve" },
        ].map((btn) => (
          <button
            key={btn.key}
            onClick={() => setFilterStatus(btn.key)}
            className={`rounded-lg px-3 py-1.5 font-semibold transition-colors ${
              filterStatus === btn.key
                ? "bg-sky-600 text-white"
                : "border border-slate-800 bg-slate-900 text-slate-300 hover:bg-slate-800"
            }`}
          >
            {btn.label}
          </button>
        ))}
      </div>

      {/* Complete 12-Attribute Verification Ledger */}
      <Card>
        <CardHeader className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            <CardTitle>
              Verified Indicator Provenance & Freshness Ledger (12 Mandatory Attributes)
            </CardTitle>
          </div>
          <Badge variant="sky">{filtered.length} INDICATORS</Badge>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-800 text-[11px] uppercase text-slate-400">
              <tr>
                <th className="py-2.5 pr-3">Indicator</th>
                <th className="py-2.5 pr-3">Verified Value</th>
                <th className="py-2.5 pr-3">Source & Tier</th>
                <th className="py-2.5 pr-3">Period / Effective</th>
                <th className="py-2.5 pr-3">Last Retrieved</th>
                <th className="py-2.5 pr-3">Age / Next SLA</th>
                <th className="py-2.5 pr-3">Freshness & Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70">
              {filtered.map((ind) => (
                <tr key={ind.indicator_code} className="hover:bg-slate-900/50">
                  <td className="py-2.5 pr-3">
                    <div className="font-semibold text-white">{ind.indicator_name}</div>
                    <div className="font-mono text-[10px] text-slate-400">
                      {ind.indicator_code} • {ind.country}
                    </div>
                  </td>
                  <td className="py-2.5 pr-3 font-mono font-bold text-emerald-300">
                    {typeof ind.value === "number" ? ind.value.toLocaleString(undefined, { maximumFractionDigits: 4 }) : ind.value}{" "}
                    <span className="text-[10px] font-normal text-slate-400">{ind.unit}</span>
                  </td>
                  <td className="py-2.5 pr-3">
                    <div className="flex items-center gap-1.5">
                      <span className="text-slate-200">{ind.source}</span>
                      {ind.source_url && (
                        <a
                          href={ind.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-sky-400 hover:text-sky-300"
                          title={ind.source_url}
                        >
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                    </div>
                    <div className="font-mono text-[10px] text-slate-400">
                      {ind.source_tier} • Conf: {ind.confidence_score}%
                    </div>
                  </td>
                  <td className="py-2.5 pr-3 font-mono text-[11px] text-slate-300">
                    <div>{ind.reporting_period}</div>
                    <div className="text-[10px] text-slate-500">Eff: {ind.effective_date}</div>
                  </td>
                  <td className="py-2.5 pr-3 font-mono text-[10px] text-slate-400">
                    {ind.retrieval_timestamp ? ind.retrieval_timestamp.slice(0, 16).replace("T", " ") : "—"}
                  </td>
                  <td className="py-2.5 pr-3 font-mono text-[11px]">
                    <div className="text-slate-200">{ind.age_days}d old</div>
                    <div className="text-[10px] text-slate-500">Next: {ind.next_expected_update}</div>
                  </td>
                  <td className="py-2.5 pr-3 space-y-1">
                    <Badge variant={freshnessBadgeVariant(ind.freshness_status)}>
                      {ind.freshness_status}
                    </Badge>
                    {ind.stale_warning && (
                      <div className="text-[10px] text-amber-400 max-w-xs leading-tight">
                        {ind.stale_warning}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Automated Cross-Source Discrepancy Audit Log (Part 1.5) */}
      <Card className="border-amber-800/50">
        <CardHeader className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-amber-400" />
            <CardTitle>
              Automated Cross-Source Discrepancy Detection & Hierarchy Resolution Log
            </CardTitle>
          </div>
          <Badge variant="amber">{discrepancies.length} LOGGED</Badge>
        </CardHeader>
        <CardContent className="space-y-3 text-xs">
          {discrepancies.length === 0 ? (
            <p className="text-slate-400">No cross-source discrepancies detected.</p>
          ) : (
            discrepancies.map((d) => (
              <div
                key={d.id}
                className="rounded-lg border border-slate-800 bg-slate-950/70 p-3.5 space-y-2"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-amber-400" />
                    <span className="font-bold text-white">{d.indicator_name}</span>
                    <span className="font-mono text-[11px] text-sky-400">({d.indicator_code})</span>
                  </div>
                  <Badge variant="emerald">{d.resolution_status}</Badge>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 font-mono text-[11px]">
                  <div className="rounded bg-emerald-950/40 border border-emerald-800/50 p-2">
                    <div className="text-emerald-400 text-[10px]">AUTHORITATIVE ({d.primary_source_tier})</div>
                    <div className="text-white font-bold text-sm">{d.authoritative_value}</div>
                    <div className="text-slate-400 text-[10px]">{d.primary_source}</div>
                  </div>
                  <div className="rounded bg-rose-950/30 border border-rose-800/40 p-2">
                    <div className="text-rose-400 text-[10px]">CONFLICTING ({d.conflicting_source_tier})</div>
                    <div className="text-slate-300 font-bold text-sm">{d.conflicting_value}</div>
                    <div className="text-slate-400 text-[10px]">{d.conflicting_source}</div>
                  </div>
                  <div className="rounded bg-slate-900 border border-slate-800 p-2">
                    <div className="text-amber-400 text-[10px]">VARIANCE & AUDIT</div>
                    <div className="text-white font-bold text-sm">
                      Δ {d.variance_abs} ({d.variance_pct}%)
                    </div>
                    <div className="text-slate-400 text-[10px]">Period: {d.reporting_period}</div>
                  </div>
                </div>
                <p className="text-[11px] text-slate-300">
                  <Clock className="inline h-3 w-3 mr-1 text-slate-400" />
                  {d.resolution_rule}
                </p>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
