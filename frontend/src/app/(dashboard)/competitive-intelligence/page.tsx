"use client";

import React, { useEffect, useState } from "react";
import { fmipApi } from "@/lib/api";
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/primitives";
import type { CompetitorEvent, CompetitorProfile } from "@/types/intelligence";

const INITIAL_EVENTS: CompetitorEvent[] = [
  {
    id: "ce-1",
    competitor_id: "c1",
    competitor_name: "Stanbic IBTC Holdings Plc",
    competitor_category: "ASSET_MANAGEMENT",
    event_type: "NEW_PRODUCT",
    event_date: "2026-11-21",
    title:
      "Aggressive Scaling of Stanbic IBTC Money Market & Dollar Fund Direct Digital Distribution",
    summary:
      "Stanbic IBTC Asset Management expanded automated mobile sweep capabilities into its Money Market and USD Dollar Funds, capturing retail and corporate liquidity seeking >20% Naira yields and USD protection.",
    what_they_are_doing_differently:
      "Integrating bank holdco current accounts, pension RSA onboarding, and mutual fund subscriptions into a single digital super-app ecosystem.",
    implications_for_our_business:
      "Raises customer acquisition bar in retail and mass-affluent asset management; standalone funds without seamless mobile onboarding risk AUM attrition.",
    recommended_counter_strategy:
      "Launch API-first embedded treasury and money-market sweep modules with transparent daily yield reporting and institutional fee tiers.",
    threat_level: "HIGH",
    source_register_id: "SEC_NIGERIA",
  },
  {
    id: "ce-2",
    competitor_id: "c2",
    competitor_name: "Chapel Hill Denham",
    competitor_category: "INVESTMENT_BANK",
    event_type: "STRATEGIC_INVESTMENT",
    event_date: "2026-11-20",
    title:
      "Expansion of Naira Infrastructure Debt & Renewable Energy Co-Investment Tranches for PFAs",
    summary:
      "Chapel Hill Denham structured additional long-tenor Naira infrastructure debt tranches anchored by Nigerian PFAs and DFI credit guarantees.",
    what_they_are_doing_differently:
      "Positioning alternative credit vehicles as inflation-indexed, PenCom-compliant substitutes for traditional FGN bonds.",
    implications_for_our_business:
      "Captures long-duration institutional management fees (1.5%–2.0% p.a.) from PFAs looking to diversify away from sovereign bonds.",
    recommended_counter_strategy:
      "Structure a niche mid-market Private Credit & Export-Agribusiness Infrastructure Debt Fund co-guaranteed by regional DFIs.",
    threat_level: "HIGH",
    source_register_id: "PENCOM",
  },
  {
    id: "ce-3",
    competitor_id: "c3",
    competitor_name: "United Capital Plc",
    competitor_category: "INVESTMENT_BANK",
    event_type: "MARKET_EXPANSION",
    event_date: "2026-11-22",
    title:
      "Commercial Paper Origination Surge & Eurobond Fund Expansion via InvestNow",
    summary:
      "United Capital accelerated FMDQ Commercial Paper arranging mandates for mid-to-large corporates priced out of 32%+ bank loans.",
    what_they_are_doing_differently:
      "Bundling CP issuance advisory with immediate distribution into internal mutual funds and retail HNI syndication.",
    implications_for_our_business:
      "Integrated origination-to-distribution shortens deal execution timelines and captures both issuing-house and fund-management fees.",
    recommended_counter_strategy:
      "Establish a dedicated Debt Capital Markets (DCM) Commercial Paper desk linked directly to our private wealth and institutional liquidity pools.",
    threat_level: "MODERATE",
    source_register_id: "FMDQ_OFFICIAL",
  },
  {
    id: "ce-4",
    competitor_id: "c4",
    competitor_name: "Guaranty Trust Holding Company Plc (GTCO)",
    competitor_category: "COMMERCIAL_BANK",
    event_type: "M_AND_A",
    event_date: "2026-11-19",
    title:
      "HoldCo Capital Deployment into Non-Bank Asset Management, Pension, and HabariPay Subsidiaries",
    summary:
      "Following recapitalisation capital raises, Tier-1 banking HoldCos (GTCO, Access Holdings) are scaling their wealth, pension, and payment subsidiaries.",
    what_they_are_doing_differently:
      "Using zero-cost retail banking touchpoints to cross-sell SEC-regulated mutual funds and pension transfers at near-zero customer acquisition cost.",
    implications_for_our_business:
      "Intensifies competition for standard retail money market products, forcing independent firms to differentiate on alpha, speed, and bespoke advisory.",
    recommended_counter_strategy:
      "Focus on high-touch HNI Family Office wealth management, corporate treasury advisory, and specialized high-yield private credit products.",
    threat_level: "HIGH",
    source_register_id: "NGX_OFFICIAL",
  },
  {
    id: "ce-5",
    competitor_id: "c5",
    competitor_name: "Moniepoint Inc",
    competitor_category: "FINTECH",
    event_type: "BUSINESS_MODEL_INNOVATION",
    event_date: "2026-11-23",
    title:
      "AI-Driven SME Working-Capital Lending & High-Yield Merchant Float Accounts",
    summary:
      "Moniepoint expanded automated working-capital credit lines and overnight merchant float yield features across its nationwide SME POS network.",
    what_they_are_doing_differently:
      "Underwriting SME credit using real-time POS settlement velocity rather than traditional collateral, and monetizing idle merchant float.",
    implications_for_our_business:
      "Creates partnership opportunities to provide institutional wholesale liquidity or securitized funding note structures to top-performing fintech lenders.",
    recommended_counter_strategy:
      "Partner with tier-1 merchant fintechs as an institutional debt arranger and asset-backed commercial paper structurer.",
    threat_level: "MODERATE",
    source_register_id: "CBN_OFFICIAL",
  },
];

export default function CompetitiveIntelligencePage() {
  const [events, setEvents] = useState<CompetitorEvent[]>(INITIAL_EVENTS);
  const [profiles, setProfiles] = useState<CompetitorProfile[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");

  useEffect(() => {
    fmipApi
      .getCompetitorEvents()
      .then((rows) => {
        if (rows && rows.length > 0) setEvents(rows);
      })
      .catch(() => {});
    fmipApi
      .getCompetitorProfiles()
      .then((rows) => {
        if (rows && rows.length > 0) setProfiles(rows);
      })
      .catch(() => {});
  }, []);

  const categories = [
    "ALL",
    "ASSET_MANAGEMENT",
    "INVESTMENT_BANK",
    "COMMERCIAL_BANK",
    "WEALTH_MANAGEMENT",
    "FINTECH",
    "INVESTMENT_PLATFORM",
  ];

  const filteredEvents = events.filter((e) =>
    selectedCategory === "ALL" ? true : e.competitor_category === selectedCategory
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <Badge variant="purple">AGENT 4: COMPETITIVE INTELLIGENCE DESK</Badge>
          <h1 className="mt-1 text-2xl font-bold text-white">
            Financial Services Competitive Intelligence & Counter-Strategy Matrix
          </h1>
          <p className="text-xs text-slate-400">
            Monitoring Asset Managers, Commercial Banks, Investment Banks, PFAs, Insurers, Fintechs, Brokerages, Platforms & Wealth Managers
          </p>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold ${
                selectedCategory === cat
                  ? "bg-purple-600 text-white"
                  : "bg-slate-800 text-slate-300 hover:bg-slate-700"
              }`}
            >
              {cat.replace(/_/g, " ")}
            </button>
          ))}
        </div>
      </div>

      {/* Competitor Strategic Moves & Counter-Strategy Feed */}
      <div className="space-y-4">
        {filteredEvents.map((ev) => (
          <Card key={ev.id || ev.title}>
            <CardHeader className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="flex items-center gap-2">
                  <Badge variant="purple">{ev.competitor_category}</Badge>
                  <Badge variant="sky">{ev.event_type}</Badge>
                  <span className="font-mono text-xs text-slate-400">
                    {ev.event_date}
                  </span>
                </div>
                <h3 className="mt-1 text-base font-bold text-white">
                  {ev.competitor_name} — {ev.title}
                </h3>
              </div>
              <Badge
                variant={
                  ev.threat_level === "HIGH"
                    ? "rose"
                    : ev.threat_level === "MODERATE"
                    ? "amber"
                    : "emerald"
                }
              >
                THREAT LEVEL: {ev.threat_level}
              </Badge>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <p className="text-slate-300 leading-relaxed">{ev.summary}</p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                  <div className="font-bold text-amber-400 mb-1">
                    What Competitor Is Doing Differently
                  </div>
                  <p className="text-slate-300 leading-relaxed">
                    {ev.what_they_are_doing_differently}
                  </p>
                </div>
                <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                  <div className="font-bold text-rose-400 mb-1">
                    Implications for Our Business
                  </div>
                  <p className="text-slate-300 leading-relaxed">
                    {ev.implications_for_our_business}
                  </p>
                </div>
                <div className="rounded-lg border border-emerald-800/50 bg-emerald-950/20 p-3">
                  <div className="font-bold text-emerald-400 mb-1">
                    Recommended Counter-Strategy
                  </div>
                  <p className="text-slate-200 leading-relaxed">
                    {ev.recommended_counter_strategy}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Institutional Competitor Profiles Directory */}
      {profiles.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Registered Nigerian Financial Services Competitor Profiles</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
            {profiles.map((p) => (
              <div
                key={p.id}
                className="rounded-lg border border-slate-800 bg-slate-950/80 p-4 space-y-2"
              >
                <div className="flex items-center justify-between">
                  <Badge variant="sky">{p.category}</Badge>
                  <span className="font-mono text-[11px] text-slate-400">{p.tier}</span>
                </div>
                <div className="text-sm font-bold text-white">{p.name}</div>
                <div className="text-slate-400">{p.aum_or_capital_estimate}</div>
                <div>
                  <span className="font-semibold text-emerald-400">Key Products: </span>
                  <span className="text-slate-300">{p.key_products.join(", ")}</span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
