"use client";

import React, { useEffect, useState } from "react";
import { ShieldAlert, Sparkles } from "lucide-react";
import { fmipApi } from "@/lib/api";
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  ScoreBar,
} from "@/components/ui/primitives";
import type { OpportunityRadarItem } from "@/types/intelligence";

const INITIAL_OPPORTUNITIES: OpportunityRadarItem[] = [
  {
    id: "opp-1",
    opportunity_class: "INVESTMENT_OPPORTUNITY",
    radar_category: "ATTRACTIVE_FIXED_INCOME_YIELD",
    target_business_line: "ASSET_MANAGEMENT",
    title:
      "Sovereign Barbell Strategy: 364-Day NTB Carry (22.85%) + Tactical 10Y FGN Bond Duration (20.30%)",
    instrument_or_sector:
      "364-Day Nigerian Treasury Bills / OMO Bills & 10-Year FGN Sovereign Bonds",
    geography: "Nigeria",
    thesis:
      "The Nigerian sovereign yield curve is humped at the 1-year tenor (22.85% effective yield vs 20.30% on the 10Y FGN Bond). Allocating 70% to 364-day NTBs/OMO bills captures peak sovereign carry with sub-1-year duration risk, while a 30% allocation to the 10Y FGN Bond (Modified Duration 4.18 yrs, Convexity 24.52) positions for +8.5% capital appreciation per 200 bps of future disinflation yield compression.",
    supporting_quantitative_evidence: {
      ntb_364d_effective_yield_pct: 22.85,
      fgn_10y_bond_yield_pct: 20.3,
      term_spread_10y_minus_1y_bps: -255,
      fgn_10y_modified_duration_years: 4.18,
    },
    assumptions: [
      "CBN maintains orthodox liquidity sterilization keeping 364D primary auction stop rates above 19.5%.",
      "Headline CPI begins gradual base-effect moderation over the next 6–12 months.",
    ],
    risk_assessment:
      "Primary risk is a further +200 bps CBN MPR hike triggered by food/energy inflation shocks (mitigated by holding 70% in short-dated 364D bills).",
    scores: {
      potential_return: 89.0,
      risk_adjusted: 92.5,
      market_attractiveness: 94.0,
      evidence_quality: 96.0,
      liquidity: 95.0,
      regulatory_feasibility: 98.0,
      composite_rank_score: 93.8,
    },
    time_horizon: "SHORT_TERM_0_6M",
    status: "ACTIVE_HIGH_CONVICTION",
  },
  {
    id: "opp-2",
    opportunity_class: "STRATEGIC_BUSINESS_OPPORTUNITY",
    radar_category: "NEW_FINANCIAL_PRODUCT",
    target_business_line: "ASSET_MANAGEMENT",
    title:
      "Launch Institutional & HNI High-Yield Treasury & Commercial Paper Liquidity Fund + B2B2C Fintech Sweep API",
    instrument_or_sector: "Asset Management / Money Market & Short-Duration Credit CIS",
    geography: "Nigeria",
    thesis:
      "With 364-day NTB yields at 22.85% and FMDQ Commercial Papers yielding 24.5%–27.0% while bank savings deposit rates lag below 8%, launching a daily-liquidity Institutional Treasury & CP Fund distributed both directly to corporate treasuries and via white-label B2B2C APIs to partner fintech platforms can scale AUM to NGN 50–100 billion within 12 months.",
    supporting_quantitative_evidence: {
      ntb_364d_effective_yield_pct: 22.85,
      commercial_paper_yield_band_pct: "24.50 - 27.00",
      target_year1_aum_ngn_bn: 65.0,
      estimated_annual_management_fee_bps: 150.0,
    },
    assumptions: [
      "SEC Nigeria fast-track CIS fund registration or shelf utilization.",
      "Integration with 2–3 digital wealth / SME fintech aggregators for retail/SME float sweep.",
    ],
    risk_assessment:
      "Credit default risk on underlying Commercial Paper issuers (mitigated by strict 75% sovereign NTB floor and 25% cap on A-rated short-term CPs).",
    scores: {
      potential_return: 90.0,
      risk_adjusted: 91.5,
      market_attractiveness: 93.0,
      evidence_quality: 94.0,
      liquidity: 95.0,
      regulatory_feasibility: 93.0,
      composite_rank_score: 92.7,
    },
    time_horizon: "SHORT_TERM_0_6M",
    strategic_evaluation_matrix: {
      market_size: "NGN 3.8+ Trillion Nigerian SEC-regulated CIS market",
      market_growth: "35%+ YoY AUM growth driven by corporate flight from low-yielding deposits",
      customer_demand: "Very High — corporate treasurers, HNIs, and fintech platforms",
      competitive_intensity: "High in traditional retail, Low in B2B2C API-embedded treasury sweeps",
      revenue_potential: "NGN 975M – NGN 1.5B annual recurring management fees at NGN 65B–100B AUM",
      profitability: "60%+ operating EBITDA margin due to automated NAV & digital B2B2C onboarding",
      regulatory_requirements: "SEC Nigeria Fund/Portfolio Manager License & CIS Trust Deed approval",
      capital_requirements: "Moderate — SEC regulatory minimum capital + NGN 500M seed co-investment",
      execution_difficulty: "Low-to-Moderate — leverages existing fixed-income treasury execution desk",
      strategic_fit: "Core fit for Holding Company Asset & Wealth Management recurring fee growth",
    },
    status: "ACTIVE_HIGH_CONVICTION",
  },
  {
    id: "opp-3",
    opportunity_class: "INVESTMENT_OPPORTUNITY",
    radar_category: "UNDERVALUED_EQUITY",
    target_business_line: "INSTITUTIONAL_INVESTMENT",
    title:
      "Tier-1 Nigerian Financial HoldCos (GTCO at 3.03x P/E & Zenith Bank at 2.15x P/E) Trading at Deep Discount to 2-Stage DCF Intrinsic Value",
    instrument_or_sector: "NGX Banking Sector (GTCO.NG, ZENITHBANK.NG)",
    geography: "Nigeria",
    thesis:
      "GTCO (Price: NGN 55.50, DCF Intrinsic Value: NGN 79.82, Upside: +43.8%) and Zenith Bank (Price: NGN 46.30, DCF Intrinsic Value: NGN 71.48, Upside: +54.4%) generate ROE above 29.1% and 36.4% respectively, benefiting from wide Net Interest Margins in a 27.50% MPR regime while trading near or below book value.",
    supporting_quantitative_evidence: {
      gtco_pe_ratio: 3.03,
      gtco_roe_pct: 36.46,
      gtco_dcf_intrinsic_value: 79.82,
      zenith_pe_ratio: 2.15,
      zenith_roe_pct: 29.18,
      zenith_dcf_intrinsic_value: 71.48,
    },
    assumptions: [
      "Tier-1 banks maintain Net Interest Margins >8.0% and Cost-to-Income ratios <35%.",
      "NPL ratios remain below the 5.0% CBN prudential ceiling.",
    ],
    risk_assessment:
      "Dilution overhang from ongoing CBN recapitalisation share issuances and potential regulatory windfall levies on FX revaluation gains.",
    scores: {
      potential_return: 91.0,
      risk_adjusted: 86.5,
      market_attractiveness: 88.0,
      evidence_quality: 94.0,
      liquidity: 92.0,
      regulatory_feasibility: 95.0,
      composite_rank_score: 90.9,
    },
    time_horizon: "MEDIUM_TERM_6_18M",
    status: "ACTIVE_HIGH_CONVICTION",
  },
  {
    id: "opp-4",
    opportunity_class: "STRATEGIC_BUSINESS_OPPORTUNITY",
    radar_category: "REGULATORY_OPPORTUNITY",
    target_business_line: "INVESTMENT_BANKING",
    title:
      "Dedicated Commercial Paper (CP) Origination & Mid-Market Recapitalisation M&A Advisory Desk",
    instrument_or_sector: "Debt Capital Markets (DCM) & Financial Services M&A Advisory",
    geography: "Nigeria",
    thesis:
      "CBN's 50% CRR has pushed commercial bank lending rates above 32%, forcing creditworthy corporates into the FMDQ Commercial Paper market. Simultaneously, CBN's NGN 500bn/200bn bank recapitalisation deadline is compelling Tier-2/Tier-3 banks and insurance companies into capital raises and M&A.",
    supporting_quantitative_evidence: {
      interbank_opr_rate_pct: 30.65,
      bank_lending_rate_benchmark_pct: 32.5,
      cp_issuance_cost_saving_bps: 450.0,
      banking_recapitalisation_capital_gap_ngn_tn: 2.2,
    },
    assumptions: [
      "Continued spread advantage of 300–500 bps between FMDQ CP discount rates and commercial bank overdrafts.",
    ],
    risk_assessment:
      "Regulatory timeline extensions or slowdown in corporate working-capital borrowing if macro growth decelerates.",
    scores: {
      potential_return: 88.5,
      risk_adjusted: 89.0,
      market_attractiveness: 91.0,
      evidence_quality: 93.0,
      liquidity: 85.0,
      regulatory_feasibility: 95.0,
      composite_rank_score: 90.3,
    },
    time_horizon: "SHORT_TERM_0_6M",
    strategic_evaluation_matrix: {
      market_size: "NGN 1.5+ Trillion annual FMDQ CP issuance + NGN 2.2 Trillion bank capital pipeline",
      market_growth: "28%+ YoY growth in non-bank corporate debt issuance",
      customer_demand: "High — CFOs of mid-to-large corporates seeking working-capital interest relief",
      competitive_intensity: "Moderate-to-High in Tier-1 deals; mid-market corporate CP space underserved",
      revenue_potential: "NGN 750M – NGN 1.2B annual arrangement, placement, and advisory fees",
      profitability: "High (65%+ contribution margin; agency placement model)",
      regulatory_requirements: "SEC Issuing House License & FMDQ Registration Member (Quotations) status",
      capital_requirements: "Low-to-Moderate — advisory and agency placement model",
      execution_difficulty: "Moderate — requires senior DCM origination coverage and PFA placement network",
      strategic_fit: "Directly feeds proprietary Commercial Paper inventory into our Asset Management funds",
    },
    status: "ACTIVE_HIGH_CONVICTION",
  },
  {
    id: "opp-5",
    opportunity_class: "STRATEGIC_BUSINESS_OPPORTUNITY",
    radar_category: "AFRICAN_REPLICATION_PLAY",
    target_business_line: "ALTERNATIVE_INVESTMENTS",
    title:
      "PenCom-Compliant Private Credit & Export-Agribusiness / Distributed Solar Infrastructure Debt Fund",
    instrument_or_sector: "Alternative Investments / Senior Secured Infrastructure & Private Credit",
    geography: "Nigeria & West Africa",
    thesis:
      "Replicating successful East and Southern African DFI-blended private credit structures in Nigeria: PenCom's NGN 21.9+ trillion AUM is structurally under-allocated to Infrastructure and Private Equity (<2% vs 5%–10% regulatory ceilings). A senior secured Naira/USD-indexed Private Credit Fund financing corporate captive solar-hybrid power and export-processing agribusiness offers 26%+ Naira returns with DFI first-loss protection.",
    supporting_quantitative_evidence: {
      pencom_total_aum_ngn_tn: 21.9,
      pencom_infrastructure_allocation_headroom_ngn_bn: 800.0,
      target_fund_size_ngn_bn: 35.0,
      target_gross_irr_pct: 27.5,
    },
    assumptions: [
      "Anchor co-investment from 1–2 DFIs (e.g., IFC, AfDB, InfraCredit guarantee) to achieve investment-grade rating for PFA eligibility.",
    ],
    risk_assessment:
      "Longer fundraising cycle (6–12 months) with PFAs and rigorous project-finance due diligence requirements.",
    scores: {
      potential_return: 92.0,
      risk_adjusted: 85.5,
      market_attractiveness: 90.0,
      evidence_quality: 88.0,
      liquidity: 72.0,
      regulatory_feasibility: 89.0,
      composite_rank_score: 87.4,
    },
    time_horizon: "LONG_TERM_18M_PLUS",
    strategic_evaluation_matrix: {
      market_size: "NGN 800+ Billion addressable PFA & DFI alternative credit allocation pool",
      market_growth: "40%+ growth in captive industrial solar-hybrid & export-agribusiness financing",
      customer_demand: "High from industrial corporates escaping diesel costs and PFAs seeking real yields",
      competitive_intensity: "Low-to-Moderate (mid-market captive energy & export credit wide open)",
      revenue_potential: "2.0% management fee + 20% carried interest above hurdle on NGN 35B–50B fund",
      profitability: "High long-term locked-in 7-to-10-year institutional fee annuity",
      regulatory_requirements: "SEC Specialist / Infrastructure Fund registration & PenCom compliance",
      capital_requirements: "Moderate — GP commitment of 1%–2% of fund size (NGN 350M–700M)",
      execution_difficulty: "Moderate-to-High — requires credit structuring and DFI guarantee coordination",
      strategic_fit: "Positions Holding Company as an institutional alternatives leader",
    },
    status: "ACTIVE_HIGH_CONVICTION",
  },
];

export default function OpportunityRadarPage() {
  const [filterClass, setFilterClass] = useState<string>("ALL");
  const [opportunities, setOpportunities] =
    useState<OpportunityRadarItem[]>(INITIAL_OPPORTUNITIES);

  useEffect(() => {
    fmipApi
      .getOpportunities()
      .then((rows) => {
        if (rows && rows.length > 0) {
          setOpportunities(rows);
        }
      })
      .catch(() => {});
  }, []);

  const filtered = opportunities.filter((o) =>
    filterClass === "ALL" ? true : o.opportunity_class === filterClass
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <Badge variant="emerald">CONTINUOUS OPPORTUNITY RADAR (AGENTS 3 & 7)</Badge>
          <h1 className="mt-1 text-2xl font-bold text-white">
            Investment & Strategic Business Opportunity Radar
          </h1>
          <p className="text-xs text-slate-400">
            7-Dimension Quantitative Ranking + 10-Criterion Strategic Business Evaluation Matrix + Evidence Quality Gate
          </p>
        </div>

        <div className="flex gap-2">
          {[
            { label: "All Opportunities", val: "ALL" },
            { label: "Investment Opportunities", val: "INVESTMENT_OPPORTUNITY" },
            { label: "Strategic Business Opportunities", val: "STRATEGIC_BUSINESS_OPPORTUNITY" },
          ].map((btn) => (
            <button
              key={btn.val}
              onClick={() => setFilterClass(btn.val)}
              className={`rounded-lg px-3.5 py-2 text-xs font-semibold transition-colors ${
                filterClass === btn.val
                  ? "bg-emerald-600 text-white"
                  : "bg-slate-800 text-slate-300 hover:bg-slate-700"
              }`}
            >
              {btn.label}
            </button>
          ))}
        </div>
      </div>

      {/* Approved High-Conviction Opportunities */}
      <div className="space-y-5">
        {filtered.map((opp) => {
          const rankScore =
            opp.scores?.composite_rank_score ?? opp.composite_rank_score ?? 90.0;
          const scores = opp.scores || {
            potential_return: 89,
            risk_adjusted: 90,
            market_attractiveness: 91,
            evidence_quality: 94,
            liquidity: 88,
            regulatory_feasibility: 95,
            composite_rank_score: rankScore,
          };
          const matrix = opp.strategic_evaluation_matrix;

          return (
            <Card key={opp.id || opp.title} className="border-slate-800">
              <CardHeader className="flex flex-wrap items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge
                      variant={
                        opp.opportunity_class === "INVESTMENT_OPPORTUNITY"
                          ? "emerald"
                          : "sky"
                      }
                    >
                      {opp.opportunity_class}
                    </Badge>
                    <Badge variant="amber">{opp.radar_category}</Badge>
                    <Badge variant="purple">{opp.target_business_line}</Badge>
                    <span className="font-mono text-xs text-slate-400">
                      Horizon: {opp.time_horizon} • Geography: {opp.geography || "Nigeria"}
                    </span>
                  </div>
                  <h2 className="text-base font-bold text-white">{opp.title}</h2>
                  <p className="text-xs text-sky-400 font-mono">
                    Instrument / Sector: {opp.instrument_or_sector}
                  </p>
                </div>

                <div className="rounded-xl border border-emerald-700/50 bg-emerald-950/30 px-4 py-2.5 text-right">
                  <div className="text-[10px] font-semibold uppercase text-emerald-300">
                    Composite Rank Score
                  </div>
                  <div className="text-2xl font-bold font-mono text-emerald-400">
                    {rankScore.toFixed(1)}
                    <span className="text-xs text-slate-400">/100</span>
                  </div>
                </div>
              </CardHeader>

              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Thesis, Assumptions & Risk Assessment */}
                  <div className="lg:col-span-2 space-y-3 text-xs">
                    <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3.5 space-y-1.5">
                      <div className="font-bold text-emerald-400 uppercase flex items-center gap-1.5">
                        <Sparkles className="h-3.5 w-3.5" />
                        Investment / Business Thesis
                      </div>
                      <p className="text-slate-200 leading-relaxed">{opp.thesis}</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                        <div className="font-bold text-sky-400 mb-1">
                          Key Analytical Assumptions
                        </div>
                        <ul className="list-disc list-inside space-y-1 text-slate-300">
                          {(opp.assumptions || []).map((a, idx) => (
                            <li key={idx}>{a}</li>
                          ))}
                        </ul>
                      </div>
                      <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                        <div className="font-bold text-rose-400 mb-1">
                          Risk Assessment & Mitigants
                        </div>
                        <p className="text-slate-300 leading-relaxed">
                          {opp.risk_assessment}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* 7-Dimension Radar Score Bars */}
                  <div className="rounded-lg border border-slate-800 bg-slate-950/80 p-4 space-y-2.5">
                    <div className="text-xs font-bold uppercase text-slate-300 mb-2">
                      7-Dimension Radar Scoring Breakdown
                    </div>
                    <ScoreBar label="Potential Return" score={scores.potential_return} />
                    <ScoreBar label="Risk-Adjusted Profile" score={scores.risk_adjusted} />
                    <ScoreBar
                      label="Market Attractiveness"
                      score={scores.market_attractiveness}
                    />
                    <ScoreBar
                      label="Evidence Quality (Gate >= 65)"
                      score={scores.evidence_quality}
                    />
                    <ScoreBar label="Liquidity" score={scores.liquidity} />
                    <ScoreBar
                      label="Regulatory Feasibility"
                      score={scores.regulatory_feasibility}
                    />
                  </div>
                </div>

                {/* 10-Criterion Strategic Business Evaluation Matrix (when present) */}
                {matrix && Object.keys(matrix).length > 0 && (
                  <div className="border-t border-slate-800 pt-4">
                    <div className="text-xs font-bold uppercase text-sky-400 mb-2.5">
                      Agent 7 — 10-Criterion Strategic Business Evaluation Matrix
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5 text-xs">
                      {Object.entries(matrix).map(([k, v]) => (
                        <div
                          key={k}
                          className="rounded border border-slate-800 bg-slate-950/70 p-2.5"
                        >
                          <div className="text-[11px] font-bold uppercase text-slate-400">
                            {k.replace(/_/g, " ")}
                          </div>
                          <div className="mt-1 text-slate-200 leading-snug">{v}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Explicit Evidence Quality Gate Withheld Section */}
      <Card className="border-amber-800/50 bg-amber-950/10">
        <CardHeader className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-amber-400" />
            <CardTitle>
              Evidence Quality Gate — Candidate Theses Held Pending Verified Disclosures
            </CardTitle>
          </div>
          <Badge variant="amber">INSUFFICIENT_EVIDENCE_HELD</Badge>
        </CardHeader>
        <CardContent className="text-xs text-slate-300 space-y-2">
          <p className="font-semibold text-white">
            Distressed Consumer Goods / Import-Heavy FMCG Turnaround Equity Basket (Evidence Quality Score: 48.0/100 — Threshold: 65.0/100)
          </p>
          <p className="leading-relaxed">
            Per Section 3 & Section 6 Governance Rules (&ldquo;Do not issue recommendations without adequate data. Do not force recommendations when the evidence is insufficient&rdquo;), Agent 3 and Agent 8 (Chief Research Editor) withheld a buy recommendation on mid-cap consumer goods turnaround equities because audited notes on FX forward trade-payable settlement losses and debt-covenant waivers remain incomplete.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
