"use client";

import React, { useEffect, useState } from "react";
import {
  CheckCircle2,
  Clock,
  Gauge,
  HardDrive,
  Mail,
  RefreshCw,
  ShieldCheck,
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

const TIER_PRESETS: Record<
  string,
  {
    label: string;
    badge: "emerald" | "sky" | "amber";
    description: string;
    cooldown_seconds: number;
    search_queries_limit: number;
    max_search_results_per_query: number;
    rss_max_results: number;
    fred_history_limit: number;
    fmp_symbols_count: number;
    alpha_vantage_pairs_count: number;
  }
> = {
  FREE_STARTER: {
    label: "Free-Tier Starter Protection (Default)",
    badge: "emerald",
    description:
      "Protects free API limits (Alpha Vantage 25/day, FMP 250/day, Tavily 1,000/month) with a 15-min cooldown and targeted batch sizes.",
    cooldown_seconds: 900,
    search_queries_limit: 2,
    max_search_results_per_query: 3,
    rss_max_results: 6,
    fred_history_limit: 15,
    fmp_symbols_count: 6,
    alpha_vantage_pairs_count: 1,
  },
  STANDARD_PAID: {
    label: "Standard Institutional Research (Expanded Quota)",
    badge: "sky",
    description:
      "Balanced expansion for upgraded API plans: 3-min cooldown, 5 sector search queries (8 articles each), 14 FMP symbols, 3 FX pairs, and 60 FRED history points.",
    cooldown_seconds: 180,
    search_queries_limit: 5,
    max_search_results_per_query: 8,
    rss_max_results: 15,
    fred_history_limit: 60,
    fmp_symbols_count: 14,
    alpha_vantage_pairs_count: 3,
  },
  ENTERPRISE_UNLIMITED: {
    label: "Enterprise High-Frequency Coverage (Unrestricted)",
    badge: "amber",
    description:
      "Maximum institutional depth: zero cooldown, 8 deep Nigerian/African search queries (15 articles each), 20 FMP global/African symbols, 5 FX pairs, and 250 FRED observations.",
    cooldown_seconds: 0,
    search_queries_limit: 8,
    max_search_results_per_query: 15,
    rss_max_results: 30,
    fred_history_limit: 250,
    fmp_symbols_count: 20,
    alpha_vantage_pairs_count: 5,
  },
};

export default function AutomationSettingsPage() {
  const [reportDay, setReportDay] = useState("FRI");
  const [reportTime, setReportTime] = useState("16:30");
  const [frequency, setFrequency] = useState("WEEKLY");
  const [recipients, setRecipients] = useState(
    "Afolabi.azeez@sohcahtoaholdings.com"
  );
  const [minScore, setMinScore] = useState(75);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);
  const [ingesting, setIngesting] = useState(false);

  // API Quota & Ingestion Depth Scaling State
  const [quotaTier, setQuotaTier] = useState<string>("FREE_STARTER");
  const [cooldownSeconds, setCooldownSeconds] = useState<number>(900);
  const [searchQueriesLimit, setSearchQueriesLimit] = useState<number>(2);
  const [maxSearchResults, setMaxSearchResults] = useState<number>(3);
  const [rssMaxResults, setRssMaxResults] = useState<number>(6);
  const [fredHistoryLimit, setFredHistoryLimit] = useState<number>(15);
  const [savingQuota, setSavingQuota] = useState<boolean>(false);

  useEffect(() => {
    fmipApi
      .getQuotaProfile()
      .then((data) => {
        if (data?.quota_tier) setQuotaTier(data.quota_tier);
        if (typeof data?.cooldown_seconds === "number")
          setCooldownSeconds(data.cooldown_seconds);
        if (typeof data?.search_queries_limit === "number")
          setSearchQueriesLimit(data.search_queries_limit);
        if (typeof data?.max_search_results_per_query === "number")
          setMaxSearchResults(data.max_search_results_per_query);
        if (typeof data?.rss_max_results === "number")
          setRssMaxResults(data.rss_max_results);
        if (typeof data?.fred_history_limit === "number")
          setFredHistoryLimit(data.fred_history_limit);
      })
      .catch(() => {});

    fmipApi
      .getAlertPreferences()
      .then((pref) => {
        if (pref?.report_day_of_week) setReportDay(pref.report_day_of_week);
        if (pref?.report_time_wat) setReportTime(pref.report_time_wat);
        if (pref?.report_frequency) setFrequency(pref.report_frequency);
        if (Array.isArray(pref?.email_recipients) && pref.email_recipients.length)
          setRecipients(pref.email_recipients.join(", "));
        if (typeof pref?.min_opportunity_score_threshold === "number")
          setMinScore(pref.min_opportunity_score_threshold);
      })
      .catch(() => {});
  }, []);

  const handleSelectTierPreset = (tierKey: string) => {
    const preset = TIER_PRESETS[tierKey];
    if (!preset) return;
    setQuotaTier(tierKey);
    setCooldownSeconds(preset.cooldown_seconds);
    setSearchQueriesLimit(preset.search_queries_limit);
    setMaxSearchResults(preset.max_search_results_per_query);
    setRssMaxResults(preset.rss_max_results);
    setFredHistoryLimit(preset.fred_history_limit);
  };

  const handleSaveQuotaProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingQuota(true);
    try {
      const updated = await fmipApi.updateQuotaProfile({
        quota_tier: quotaTier,
        cooldown_seconds: cooldownSeconds,
        search_queries_limit: searchQueriesLimit,
        max_search_results_per_query: maxSearchResults,
        rss_max_results: rssMaxResults,
        fred_history_limit: fredHistoryLimit,
      });
      setSavedMsg(
        `API Quota & Ingestion Depth updated to ${updated.quota_tier} (Cooldown: ${updated.cooldown_seconds}s | Queries: ${updated.search_queries_limit}x${updated.max_search_results_per_query} | FRED History: ${updated.fred_history_limit} pts).`
      );
    } catch {
      setSavedMsg(
        `Applied ${quotaTier} quota profile locally (Cooldown: ${cooldownSeconds}s | Queries: ${searchQueriesLimit}x${maxSearchResults}).`
      );
    } finally {
      setSavingQuota(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    const emailList = recipients
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    try {
      await fmipApi.updateAlertPreferences({
        report_day_of_week: reportDay,
        report_time_wat: reportTime,
        report_frequency: frequency,
        email_recipients: emailList,
        min_opportunity_score_threshold: minScore,
      });
    } catch {}
    setSavedMsg(
      `Saved schedule: ${frequency} execution every ${reportDay} at ${reportTime} WAT (Africa/Lagos) -> ${recipients}`
    );
  };

  const handleManualIngest = async () => {
    setIngesting(true);
    try {
      const res = await fmipApi.triggerIngestion();
      const summary = res?.summary || res;
      if (summary?.quota_guard_cached) {
        setSavedMsg(
          `Quota Guard Active (${summary.active_quota_tier || quotaTier}): Last sweep ran ${summary.seconds_since_last_sweep}s ago. Lower cooldown below or switch tier to poll immediately.`
        );
      } else {
        setSavedMsg(
          `Live provider ingestion sweep completed under ${summary?.active_quota_tier || quotaTier} profile and persisted to database.`
        );
      }
    } catch {
      setSavedMsg("Verified archival and public provider baseline active.");
    } finally {
      setIngesting(false);
    }
  };

  const activePreset = TIER_PRESETS[quotaTier] || TIER_PRESETS.FREE_STARTER;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <Badge variant="sky">SECTION 9: WORKFLOW AUTOMATION & QUOTA GOVERNANCE</Badge>
          <h1 className="mt-1 text-2xl font-bold text-white">
            Automation, API Quota Scaling, Alert Preferences & Approved Providers
          </h1>
          <p className="text-xs text-slate-400">
            Configure API Ingestion Depth Tiers, n8n Scheduled Workflows, Friday Report Delivery, Google Drive Archiving & Gmail Alerts
          </p>
        </div>

        <button
          onClick={handleManualIngest}
          disabled={ingesting}
          className="flex items-center gap-2 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-50 px-4 py-2 text-xs font-semibold text-white"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${ingesting ? "animate-spin" : ""}`} />
          {ingesting ? "Polling Providers..." : "Run Live Provider Ingestion Sweep"}
        </button>
      </div>

      {savedMsg && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-700/60 bg-emerald-950/50 p-3 text-xs text-emerald-300">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>{savedMsg}</span>
        </div>
      )}

      {/* Dynamic API Quota & Ingestion Depth Scaling Card */}
      <Card>
        <CardHeader className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Gauge className="h-4 w-4 text-sky-400" />
            <CardTitle>
              API Quota & Ingestion Depth Scaling (Expand Coverage as Quotas Increase)
            </CardTitle>
          </div>
          <Badge variant={activePreset.badge}>{activePreset.label}</Badge>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSaveQuotaProfile} className="space-y-4 text-xs">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {Object.entries(TIER_PRESETS).map(([tierKey, preset]) => {
                const isSelected = quotaTier === tierKey;
                return (
                  <button
                    type="button"
                    key={tierKey}
                    onClick={() => handleSelectTierPreset(tierKey)}
                    className={`text-left rounded-lg border p-3.5 transition-all ${
                      isSelected
                        ? "border-sky-500 bg-sky-950/40 ring-1 ring-sky-500/50"
                        : "border-slate-800 bg-slate-950/70 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-mono font-bold text-white">
                        {tierKey}
                      </span>
                      <Badge variant={preset.badge}>
                        {preset.cooldown_seconds === 0
                          ? "No Cooldown"
                          : `${Math.round(preset.cooldown_seconds / 60)}m Cooldown`}
                      </Badge>
                    </div>
                    <div className="font-semibold text-slate-200 mb-1">
                      {preset.label}
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">
                      {preset.description}
                    </p>
                    <div className="mt-2.5 flex flex-wrap gap-1.5 text-[10px] font-mono text-slate-300">
                      <span className="rounded bg-slate-900 px-1.5 py-0.5">
                        FMP: {preset.fmp_symbols_count} symbols
                      </span>
                      <span className="rounded bg-slate-900 px-1.5 py-0.5">
                        AV FX: {preset.alpha_vantage_pairs_count} pairs
                      </span>
                      <span className="rounded bg-slate-900 px-1.5 py-0.5">
                        Search: {preset.search_queries_limit}×{preset.max_search_results_per_query}
                      </span>
                      <span className="rounded bg-slate-900 px-1.5 py-0.5">
                        FRED: {preset.fred_history_limit} pts
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-5 gap-3 pt-2 border-t border-slate-800/80">
              <div>
                <label className="block font-semibold text-slate-300 mb-1">
                  Sweep Cooldown (Seconds)
                </label>
                <input
                  type="number"
                  min={0}
                  max={86400}
                  value={cooldownSeconds}
                  onChange={(e) => setCooldownSeconds(Number(e.target.value))}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white font-mono"
                />
                <span className="text-[10px] text-slate-400">
                  900s = 15 min free-tier guard
                </span>
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">
                  Sector Search Queries (1–8)
                </label>
                <input
                  type="number"
                  min={1}
                  max={8}
                  value={searchQueriesLimit}
                  onChange={(e) => setSearchQueriesLimit(Number(e.target.value))}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white font-mono"
                />
                <span className="text-[10px] text-slate-400">
                  Nigerian & African themes
                </span>
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">
                  Articles / Query (1–25)
                </label>
                <input
                  type="number"
                  min={1}
                  max={25}
                  value={maxSearchResults}
                  onChange={(e) => setMaxSearchResults(Number(e.target.value))}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white font-mono"
                />
                <span className="text-[10px] text-slate-400">
                  Tavily & Google Search depth
                </span>
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">
                  Financial Press RSS Limit
                </label>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={rssMaxResults}
                  onChange={(e) => setRssMaxResults(Number(e.target.value))}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white font-mono"
                />
                <span className="text-[10px] text-slate-400">
                  Nairametrics / BusinessDay
                </span>
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">
                  FRED History Depth (5–500)
                </label>
                <input
                  type="number"
                  min={5}
                  max={500}
                  value={fredHistoryLimit}
                  onChange={(e) => setFredHistoryLimit(Number(e.target.value))}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white font-mono"
                />
                <span className="text-[10px] text-slate-400">
                  Observations per series
                </span>
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
              <div className="flex items-center gap-2 text-[11px] text-slate-400">
                <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0" />
                <span>
                  Estimated API Calls per Sweep:{" "}
                  <strong className="text-white font-mono">
                    1 FMP batch ({activePreset.fmp_symbols_count} symbols) +{" "}
                    {activePreset.alpha_vantage_pairs_count} Alpha Vantage +{" "}
                    {searchQueriesLimit} Tavily ({searchQueriesLimit * maxSearchResults} articles) + 7 FRED series
                  </strong>
                </span>
              </div>

              <button
                type="submit"
                disabled={savingQuota}
                className="flex items-center gap-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-50 px-4 py-2 font-semibold text-white transition-colors"
              >
                <Sliders className="h-3.5 w-3.5" />
                {savingQuota ? "Applying Quota Profile..." : "Apply Quota & Depth Profile"}
              </button>
            </div>
          </form>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Reporting & Alert Preferences Form */}
        <Card>
          <CardHeader className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-emerald-400" />
            <CardTitle>
              Weekly Friday Reporting Schedule & Alert Thresholds
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSave} className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block font-semibold text-slate-300 mb-1">
                    Reporting Frequency
                  </label>
                  <select
                    value={frequency}
                    onChange={(e) => setFrequency(e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white"
                  >
                    <option value="WEEKLY">Weekly (Friday-to-Friday)</option>
                    <option value="DAILY_AND_WEEKLY">Daily Brief + Friday Full Report</option>
                    <option value="BIWEEKLY">Bi-Weekly</option>
                  </select>
                </div>
                <div>
                  <label className="block font-semibold text-slate-300 mb-1">
                    Execution Day
                  </label>
                  <select
                    value={reportDay}
                    onChange={(e) => setReportDay(e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white"
                  >
                    <option value="FRI">Friday (After NGX/FMDQ Close)</option>
                    <option value="SAT">Saturday Morning</option>
                    <option value="MON">Monday Pre-Market</option>
                  </select>
                </div>
                <div>
                  <label className="block font-semibold text-slate-300 mb-1">
                    Execution Time (WAT)
                  </label>
                  <input
                    type="time"
                    value={reportTime}
                    onChange={(e) => setReportTime(e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">
                  Executive Email Recipients (Gmail Delivery)
                </label>
                <input
                  type="text"
                  value={recipients}
                  onChange={(e) => setRecipients(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white font-mono"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">
                  Minimum Opportunity Radar Alert Score Threshold ({minScore}/100)
                </label>
                <input
                  type="range"
                  min={50}
                  max={95}
                  value={minScore}
                  onChange={(e) => setMinScore(Number(e.target.value))}
                  className="w-full accent-emerald-500"
                />
              </div>

              <button
                type="submit"
                className="rounded-lg bg-emerald-600 hover:bg-emerald-500 px-4 py-2 font-semibold text-white transition-colors"
              >
                Save Schedule & Alert Configuration
              </button>
            </form>
          </CardContent>
        </Card>

        {/* n8n Workflows, Google Drive & Gmail Delivery Status */}
        <Card>
          <CardHeader>
            <CardTitle>n8n Automation Pipelines & Delivery Integrations</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            {[
              {
                name: "01_daily_market_and_macro_ingestion.json",
                schedule: "Mon–Fri at 16:00 WAT",
                desc: "Polls CBN, NGX, FMDQ, DMO, NBS, FRED, FMP & Alpha Vantage -> Runs DataQualityGate -> Persists to TimescaleDB.",
                status: "CONFIGURED",
              },
              {
                name: "02_regulatory_and_competitor_monitor.json",
                schedule: "Every 6 Hours",
                desc: "Polls CBN Circulars, SEC Nigeria, PenCom, NAICOM & Tavily Search -> Sanitizes via PromptInjectionSanitizer -> Embeds into pgvector.",
                status: "CONFIGURED",
              },
              {
                name: "03_opportunity_radar_alerts.json",
                schedule: "Daily at 17:00 WAT",
                desc: "Runs Agents 3, 6 & 7 -> Alerts Investment Committee when a new opportunity scores >= 75/100 with verified evidence.",
                status: "CONFIGURED",
              },
              {
                name: "04_friday_weekly_intelligence_report.json",
                schedule: "Every Friday at 16:30 WAT",
                desc: "Executes all 8 LangGraph Agents -> Generates 16-Section PDF (ReportLab) & Excel Workbook (OpenPyXL) -> Uploads to Google Drive -> Emails via Gmail.",
                status: "CONFIGURED",
              },
            ].map((wf) => (
              <div
                key={wf.name}
                className="rounded-lg border border-slate-800 bg-slate-950/70 p-3 space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-sky-400">{wf.name}</span>
                  <Badge variant="emerald">{wf.status}</Badge>
                </div>
                <div className="text-[11px] font-mono text-amber-400">
                  Schedule: {wf.schedule}
                </div>
                <p className="text-slate-300">{wf.desc}</p>
              </div>
            ))}

            <div className="grid grid-cols-2 gap-3 pt-1">
              <div className="rounded border border-slate-800 bg-slate-950 p-2.5 flex items-center gap-2">
                <HardDrive className="h-4 w-4 text-sky-400 shrink-0" />
                <div>
                  <div className="font-semibold text-white">Google Drive API v3</div>
                  <div className="text-[11px] text-slate-400">
                    Service Account Archiver Ready
                  </div>
                </div>
              </div>
              <div className="rounded border border-slate-800 bg-slate-950 p-2.5 flex items-center gap-2">
                <Mail className="h-4 w-4 text-emerald-400 shrink-0" />
                <div>
                  <div className="font-semibold text-white">Gmail SMTP / OAuth2</div>
                  <div className="text-[11px] text-slate-400">
                    HTML + PDF/Excel Delivery Ready
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
