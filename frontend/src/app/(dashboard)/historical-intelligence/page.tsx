"use client";

import React, { useEffect, useState } from "react";
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  GitBranch,
  History,
  Sliders,
} from "lucide-react";
import { fmipApi } from "@/lib/api";
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/primitives";

type Horizon = "1W" | "1M" | "3M" | "6M" | "1Y";

export default function HistoricalIntelligencePage() {
  const [horizon, setHorizon] = useState<Horizon>("3M");
  const [compData, setCompData] = useState<any>(null);
  const [kgData, setKgData] = useState<any>(null);

  // Interactive Custom Scenario Stress Tester State (Vision #4)
  const [mprShock, setMprShock] = useState<number>(150);
  const [infShock, setInfShock] = useState<number>(200);
  const [fxDepr, setFxDepr] = useState<number>(10);
  const [oilPrice, setOilPrice] = useState<number>(75);
  const [fedShock, setFedShock] = useState<number>(50);
  const [borrowingShock, setBorrowingShock] = useState<number>(15);
  const [stressResult, setStressResult] = useState<any>(null);
  const [runningStress, setRunningStress] = useState(false);

  const loadComparison = async (h: Horizon) => {
    try {
      const res = await fmipApi.getHistoricalComparison(h);
      setCompData(res);
    } catch {}
  };

  const runStress = async () => {
    setRunningStress(true);
    try {
      const res = await fmipApi.runCustomScenarioStressTest({
        mpr_shock_bps: mprShock,
        inflation_shock_bps: infShock,
        fx_depreciation_pct: fxDepr,
        crude_oil_price_usd: oilPrice,
        us_fed_shock_bps: fedShock,
        govt_borrowing_shock_pct: borrowingShock,
        portfolio_value_ngn: 10_000_000_000,
      });
      setStressResult(res);
    } catch {} finally {
      setRunningStress(false);
    }
  };

  useEffect(() => {
    loadComparison(horizon);
  }, [horizon]);

  useEffect(() => {
    fmipApi.getKnowledgeGraph().then(setKgData).catch(() => {});
    runStress();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const comparisons: any[] = compData?.comparisons || [];
  const edges: any[] = kgData?.edges || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <Badge variant="sky">PART 5B & VISION #3–#4: HISTORICAL & SCENARIO INTELLIGENCE</Badge>
          <h1 className="mt-1 text-2xl font-bold text-white">
            Historical Market Comparison (1W–1Y), Custom Stress Testing & Knowledge Graph
          </h1>
          <p className="text-xs text-slate-400">
            Compare verified Nigerian & Global indicators across 5 horizons, stress-test custom macro shocks, and explore institutional cross-market relationships.
          </p>
        </div>

        <div className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-950 p-1">
          {(["1W", "1M", "3M", "6M", "1Y"] as Horizon[]).map((h) => (
            <button
              key={h}
              onClick={() => setHorizon(h)}
              className={`rounded-md px-3 py-1.5 text-xs font-mono font-bold transition-colors ${
                horizon === h
                  ? "bg-emerald-600 text-white"
                  : "text-slate-400 hover:text-white hover:bg-slate-800"
              }`}
            >
              {h}
            </button>
          ))}
        </div>
      </div>

      {/* Historical Comparison Table */}
      <Card>
        <CardHeader className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-emerald-400" />
            <CardTitle>
              Verified Historical Market & Macro Comparison ({horizon} Horizon)
            </CardTitle>
          </div>
          <Badge variant="emerald">{comparisons.length} TRACKED SERIES</Badge>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-800 text-[11px] uppercase text-slate-400">
              <tr>
                <th className="py-2 pr-3">Indicator</th>
                <th className="py-2 pr-3">Baseline ({horizon} Ago)</th>
                <th className="py-2 pr-3">Current Verified</th>
                <th className="py-2 pr-3">Absolute Δ</th>
                <th className="py-2 pr-3">% Change</th>
                <th className="py-2 pr-3">Source Tier</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {comparisons.slice(0, 20).map((c) => {
                const isUp = c.absolute_change > 0;
                const isDown = c.absolute_change < 0;
                return (
                  <tr key={`${c.domain}-${c.code}`} className="hover:bg-slate-900/40">
                    <td className="py-2.5 pr-3">
                      <div className="font-semibold text-white">{c.name}</div>
                      <div className="font-mono text-[10px] text-slate-400">
                        {c.code} • {c.domain} ({c.unit})
                      </div>
                    </td>
                    <td className="py-2.5 pr-3 font-mono text-slate-300">
                      <div>{c.baseline_value.toLocaleString(undefined, { maximumFractionDigits: 2 })}</div>
                      <div className="text-[10px] text-slate-500">{c.baseline_date}</div>
                    </td>
                    <td className="py-2.5 pr-3 font-mono font-bold text-white">
                      <div>{c.current_value.toLocaleString(undefined, { maximumFractionDigits: 2 })}</div>
                      <div className="text-[10px] text-slate-500">{c.current_date}</div>
                    </td>
                    <td className="py-2.5 pr-3 font-mono">
                      <span className={isUp ? "text-emerald-400" : isDown ? "text-rose-400" : "text-slate-400"}>
                        {isUp ? "+" : ""}
                        {c.absolute_change.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                      </span>
                    </td>
                    <td className="py-2.5 pr-3 font-mono font-semibold">
                      <span className={`inline-flex items-center gap-1 ${isUp ? "text-emerald-400" : isDown ? "text-rose-400" : "text-slate-400"}`}>
                        {isUp && <ArrowUpRight className="h-3.5 w-3.5" />}
                        {isDown && <ArrowDownRight className="h-3.5 w-3.5" />}
                        {c.pct_change > 0 ? "+" : ""}
                        {c.pct_change}%
                      </span>
                    </td>
                    <td className="py-2.5 pr-3">
                      <Badge variant={c.source_tier === "TIER_1_OFFICIAL" ? "emerald" : "slate"}>
                        {c.source_tier}
                      </Badge>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Interactive Custom Scenario Planning & Stress Testing Engine (Vision #4) */}
      <Card className="border-sky-800/60">
        <CardHeader className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Sliders className="h-4 w-4 text-sky-400" />
            <CardTitle>
              Interactive Scenario Planning & Stress Testing Engine (Anchored to Live CBN Baseline)
            </CardTitle>
          </div>
          <Badge variant="sky">NGN 10.0B REFERENCE PORTFOLIO</Badge>
        </CardHeader>
        <CardContent className="space-y-4 text-xs">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div>
              <label className="block text-slate-300 font-semibold mb-1">MPR Shock (bps)</label>
              <input type="number" value={mprShock} onChange={(e) => setMprShock(Number(e.target.value))} className="w-full rounded border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-white font-mono" />
            </div>
            <div>
              <label className="block text-slate-300 font-semibold mb-1">CPI Shock (bps)</label>
              <input type="number" value={infShock} onChange={(e) => setInfShock(Number(e.target.value))} className="w-full rounded border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-white font-mono" />
            </div>
            <div>
              <label className="block text-slate-300 font-semibold mb-1">FX Depr. (%)</label>
              <input type="number" value={fxDepr} onChange={(e) => setFxDepr(Number(e.target.value))} className="w-full rounded border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-white font-mono" />
            </div>
            <div>
              <label className="block text-slate-300 font-semibold mb-1">Crude Oil ($/bbl)</label>
              <input type="number" value={oilPrice} onChange={(e) => setOilPrice(Number(e.target.value))} className="w-full rounded border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-white font-mono" />
            </div>
            <div>
              <label className="block text-slate-300 font-semibold mb-1">US Fed (bps)</label>
              <input type="number" value={fedShock} onChange={(e) => setFedShock(Number(e.target.value))} className="w-full rounded border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-white font-mono" />
            </div>
            <div>
              <label className="block text-slate-300 font-semibold mb-1">Govt Borrow (%)</label>
              <input type="number" value={borrowingShock} onChange={(e) => setBorrowingShock(Number(e.target.value))} className="w-full rounded border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-white font-mono" />
            </div>
          </div>

          <button
            onClick={runStress}
            disabled={runningStress}
            className="flex items-center gap-2 rounded-lg bg-sky-600 hover:bg-sky-500 px-4 py-2 font-semibold text-white"
          >
            <Activity className="h-3.5 w-3.5" />
            {runningStress ? "Computing Scenarios..." : "Run Base / Bull / Bear Stress Simulation"}
          </button>

          {stressResult?.scenarios && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
              {["bull_case", "base_case", "bear_case"].map((key) => {
                const sc = stressResult.scenarios[key];
                const variant = key === "bull_case" ? "emerald" : key === "base_case" ? "sky" : "rose";
                return (
                  <div key={key} className="rounded-lg border border-slate-800 bg-slate-950/80 p-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <Badge variant={variant}>{sc.scenario_band}</Badge>
                      <span className={`font-mono font-bold text-sm ${sc.portfolio_total_impact_pct >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                        {sc.portfolio_total_impact_pct >= 0 ? "+" : ""}
                        {sc.portfolio_total_impact_pct}%
                      </span>
                    </div>
                    <div className="font-mono text-[11px] text-slate-300">
                      Est. P&amp;L: <strong className="text-white">NGN {(sc.portfolio_pnl_ngn / 1e6).toFixed(1)}M</strong>
                    </div>
                    <div className="text-[11px] text-slate-400 space-y-0.5 font-mono">
                      <div>Projected MPR: {sc.projected_mpr_pct}% | CPI: {sc.projected_cpi_pct}%</div>
                      <div>10Y FGN Bond Impact: {sc.asset_class_impacts_pct.fgn_bonds_10y_pct}%</div>
                      <div>NGX Equities Impact: {sc.asset_class_impacts_pct.ngx_equities_pct}%</div>
                      <div>USD Assets (NGN): {sc.asset_class_impacts_pct.usd_eurobonds_ngn_terms_pct}%</div>
                    </div>
                    <p className="text-[11px] text-slate-300 pt-1 border-t border-slate-800/80">
                      <strong>AM Desk:</strong> {sc.business_line_implications.asset_management}
                    </p>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Institutional Knowledge Graph Explorer (Vision #3) */}
      <Card>
        <CardHeader className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-amber-400" />
            <CardTitle>
              Institutional Knowledge Graph (Cross-Market & Regulatory Causal Linkages)
            </CardTitle>
          </div>
          <Badge variant="amber">
            {kgData?.nodes?.length || 0} NODES • {edges.length} RELATIONSHIPS
          </Badge>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          {edges.map((e) => (
            <div key={e.id} className="rounded-lg border border-slate-800 bg-slate-950/70 p-3 space-y-1.5">
              <div className="flex flex-wrap items-center gap-1.5 font-mono text-[11px]">
                <span className="rounded bg-slate-800 px-2 py-0.5 text-emerald-300">{e.source_label}</span>
                <span className="text-amber-400 font-bold">--[{e.relationship_type}]--&gt;</span>
                <span className="rounded bg-slate-800 px-2 py-0.5 text-sky-300">{e.target_label}</span>
              </div>
              <p className="text-slate-300 leading-relaxed">{e.evidence_summary}</p>
              <div className="text-[10px] font-mono text-slate-500">
                Confidence: {e.confidence_score}%
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
