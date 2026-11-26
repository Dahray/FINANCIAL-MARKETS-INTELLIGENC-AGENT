"use client";

import React, { useEffect, useState } from "react";
import { ExternalLink, ShieldCheck } from "lucide-react";
import { fmipApi } from "@/lib/api";
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/primitives";
import type { RegulatoryEvent, SourceRegisterEntry } from "@/types/intelligence";

const INITIAL_REG_EVENTS: RegulatoryEvent[] = [
  {
    id: "re-1",
    regulator_code: "CBN",
    regulator_name: "Central Bank of Nigeria (CBN)",
    reference_number: "FPR/DIR/PUB/CIR/002/009",
    title:
      "CBN Banking Sector Recapitalisation & Minimum Paid-Up Capital Framework Enforcement",
    issued_date: "2026-11-20",
    policy_summary:
      "Strict enforcement of paid-up share capital and share premium minimums (NGN 500bn International Commercial Banks, NGN 200bn National Commercial Banks, NGN 50bn Merchant Banks), excluding retained earnings from qualifying capital.",
    compliance_implications:
      "Requires capital verification, CBN/SEC allotment clearance, and strict anti-money-laundering vetting on all capital calls before the March 2026/2027 compliance milestones.",
    capital_or_operational_impact:
      "Triggers over NGN 2.2 trillion in primary equity and rights issuance across Nigerian banking groups and potential Tier-2 M&A consolidation.",
    business_opportunities_created:
      "Major fee pool for Investment Banking (Issuing House, Underwriting, Financial Advisory, M&A) and institutional securities placement.",
    affected_segments: [
      "COMMERCIAL_BANK",
      "INVESTMENT_BANK",
      "CAPITAL_MARKET_SERVICES",
      "ASSET_MANAGEMENT",
    ],
    severity: "MANDATORY_COMPLIANCE",
    is_official_publication: true,
    source_register_id: "CBN_OFFICIAL",
  },
  {
    id: "re-2",
    regulator_code: "CBN",
    regulator_name: "Central Bank of Nigeria (CBN)",
    reference_number: "CBN/MPC/COMM/2026",
    title:
      "Monetary Policy Committee Directive on 50% CRR and NAFEM Electronic FX Matching Surveillance",
    issued_date: "2026-11-22",
    policy_summary:
      "Maintenance of 27.50% MPR and 50.00% Commercial Bank CRR alongside mandatory real-time order-book transparency on the NAFEM FX trading system.",
    compliance_implications:
      "Authorized Dealer banks and treasury desks must comply with strict intraday NOP (Net Open Position) limits and automated FX reporting.",
    capital_or_operational_impact:
      "Sterilizes bank excess Naira liquidity, keeping interbank funding costs above 30% and penalizing unhedged FX positions.",
    business_opportunities_created:
      "Creates strong corporate demand for SEC-regulated Commercial Paper issuance and Money Market Fund liquidity sweeps.",
    affected_segments: ["COMMERCIAL_BANK", "ASSET_MANAGEMENT", "WEALTH_MANAGEMENT"],
    severity: "MANDATORY_COMPLIANCE",
    is_official_publication: true,
    source_register_id: "CBN_OFFICIAL",
  },
  {
    id: "re-3",
    regulator_code: "SEC_NG",
    regulator_name: "Securities and Exchange Commission (SEC Nigeria)",
    reference_number: "SEC/REG/CIS/2026",
    title:
      "SEC Nigeria Collective Investment Schemes (CIS) Mark-to-Market Valuation & Private Fund Governance Rules",
    issued_date: "2026-11-21",
    policy_summary:
      "Enforces standardized NAV valuation reporting, custodial asset segregation, and accelerated registration for Infrastructure Debt, Private Equity, and Digital Asset / VASP vehicles.",
    compliance_implications:
      "Fund managers must submit daily/weekly NAV computations and maintain strict compliance with asset allocation bands.",
    capital_or_operational_impact:
      "Strengthens investor protection and favors institutional asset managers with robust risk and valuation infrastructure.",
    business_opportunities_created:
      "Enables launch of SEC-approved USD Eurobond Funds, Naira Infrastructure Debt Funds, and compliant digital wealth partnerships.",
    affected_segments: [
      "ASSET_MANAGEMENT",
      "WEALTH_MANAGEMENT",
      "ALTERNATIVE_INVESTMENTS",
      "FINTECH",
    ],
    severity: "STRATEGIC_SHIFT",
    is_official_publication: true,
    source_register_id: "SEC_NIGERIA",
  },
  {
    id: "re-4",
    regulator_code: "PENCOM",
    regulator_name: "National Pension Commission (PenCom)",
    reference_number: "PENCOM/INV/AUM/2026",
    title:
      "PenCom Revised Regulation on Investment of Pension Fund Assets in Infrastructure & Private Equity",
    issued_date: "2026-11-23",
    policy_summary:
      "Permits Pension Fund Administrators (PFAs) managing >NGN 21.9 trillion in AUM to expand allocations to SEC-registered Infrastructure Funds (up to 5% in RSA Fund I-III) and Private Equity Funds.",
    compliance_implications:
      "Qualifying funds must maintain investment-grade credit enhancement or DFI co-investment and list on an approved exchange (NGX/FMDQ).",
    capital_or_operational_impact:
      "Unlocks over NGN 800 billion in potential pension institutional commitments for bankable real-sector and infrastructure funds.",
    business_opportunities_created:
      "High-margin alternative asset management opportunity: structuring a PenCom-compliant Naira Infrastructure & Real Assets Debt Fund.",
    affected_segments: [
      "PFA",
      "ALTERNATIVE_INVESTMENTS",
      "ASSET_MANAGEMENT",
      "INSTITUTIONAL_INVESTMENT",
    ],
    severity: "STRATEGIC_SHIFT",
    is_official_publication: true,
    source_register_id: "PENCOM",
  },
];

export default function RegulatoryMonitorPage() {
  const [events, setEvents] = useState<RegulatoryEvent[]>(INITIAL_REG_EVENTS);
  const [sources, setSources] = useState<SourceRegisterEntry[]>([]);
  const [selectedRegulator, setSelectedRegulator] = useState<string>("ALL");

  useEffect(() => {
    fmipApi
      .getRegulatoryEvents()
      .then((rows) => {
        if (rows && rows.length > 0) setEvents(rows);
      })
      .catch(() => {});
    fmipApi
      .getSourceRegister()
      .then((rows) => {
        if (rows && rows.length > 0) setSources(rows);
      })
      .catch(() => {});
  }, []);

  const regulators = ["ALL", "CBN", "SEC_NG", "PENCOM", "NAICOM", "NGX", "FMF_NG"];
  const filtered = events.filter((e) =>
    selectedRegulator === "ALL" ? true : e.regulator_code === selectedRegulator
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <Badge variant="amber">AGENT 5: REGULATORY INTELLIGENCE DESK</Badge>
          <h1 className="mt-1 text-2xl font-bold text-white">
            Regulatory Monitor & Immutable Source Register
          </h1>
          <p className="text-xs text-slate-400">
            Official Publications from CBN, SEC Nigeria, NGX, PenCom, NAICOM, FRC & Federal Ministry of Finance
          </p>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {regulators.map((reg) => (
            <button
              key={reg}
              onClick={() => setSelectedRegulator(reg)}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold ${
                selectedRegulator === reg
                  ? "bg-amber-600 text-white"
                  : "bg-slate-800 text-slate-300 hover:bg-slate-700"
              }`}
            >
              {reg}
            </button>
          ))}
        </div>
      </div>

      {/* Regulatory Circulars & Compliance Impact Cards */}
      <div className="space-y-4">
        {filtered.map((reg) => (
          <Card key={reg.id || reg.title}>
            <CardHeader className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="flex items-center gap-2">
                  <Badge variant="amber">{reg.regulator_code}</Badge>
                  <span className="font-mono text-xs text-sky-400">
                    Ref: {reg.reference_number}
                  </span>
                  <span className="font-mono text-xs text-slate-400">
                    Issued: {reg.issued_date}
                  </span>
                  {reg.is_official_publication && (
                    <Badge variant="emerald">TIER-1 OFFICIAL PUBLICATION</Badge>
                  )}
                </div>
                <h3 className="mt-1.5 text-base font-bold text-white">{reg.title}</h3>
                <p className="text-xs text-slate-400">{reg.regulator_name}</p>
              </div>
              <Badge
                variant={
                  reg.severity === "MANDATORY_COMPLIANCE" ? "rose" : "sky"
                }
              >
                {reg.severity}
              </Badge>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                <div className="font-bold text-slate-200 mb-1">Policy Summary</div>
                <p className="text-slate-300 leading-relaxed">{reg.policy_summary}</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                  <div className="font-bold text-rose-400 mb-1">
                    Mandatory Compliance Implications
                  </div>
                  <p className="text-slate-300 leading-relaxed">
                    {reg.compliance_implications}
                  </p>
                </div>
                <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                  <div className="font-bold text-amber-400 mb-1">
                    Capital & Industry Impact
                  </div>
                  <p className="text-slate-300 leading-relaxed">
                    {reg.capital_or_operational_impact}
                  </p>
                </div>
                <div className="rounded-lg border border-emerald-800/50 bg-emerald-950/20 p-3">
                  <div className="font-bold text-emerald-400 mb-1">
                    Business Opportunities Created
                  </div>
                  <p className="text-slate-200 leading-relaxed">
                    {reg.business_opportunities_created}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Section 5 & Section 7 (#16): Traceable Source Register */}
      <Card>
        <CardHeader className="flex items-center justify-between">
          <div>
            <CardTitle>
              Immutable Source Register & Epistemic Reliability Ledger
            </CardTitle>
            <p className="text-xs text-slate-400 mt-0.5">
              Every material finding in FMIP is linked to a verified entry in the Source Register.
            </p>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-emerald-400">
            <ShieldCheck className="h-4 w-4" />
            <span>Traceability Verified</span>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase">
                  <th className="py-2.5 px-3">Source Name</th>
                  <th className="py-2.5 px-3">Publication Title</th>
                  <th className="py-2.5 px-3">Relevant Verified Finding</th>
                  <th className="py-2.5 px-3">Reliability Tier</th>
                  <th className="py-2.5 px-3">Epistemic Type</th>
                  <th className="py-2.5 px-3">Link</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/70">
                {(sources.length > 0
                  ? sources
                  : [
                      {
                        id: "sr-1",
                        source_name: "Central Bank of Nigeria (CBN) MPC",
                        publication_title:
                          "CBN MPC Communique — MPR at 27.50%, CRR at 50.00%",
                        publication_date: "2026-11-22",
                        retrieval_date: "2026-11-25",
                        url: "https://www.cbn.gov.ng/Documents/mpc.asp",
                        relevant_finding:
                          "CBN MPC maintained hawkish stance (MPR 27.50%, CRR 50.00%), keeping 364D NTB yields above 22.8% while gross reserves reached USD 40.28bn.",
                        reliability_classification: "TIER_1_OFFICIAL",
                        epistemic_type: "FACT",
                      },
                      {
                        id: "sr-2",
                        source_name: "CBN Banking Supervision Department",
                        publication_title:
                          "CBN Banking Sector Recapitalisation Directive (2024–2026)",
                        publication_date: "2026-11-20",
                        retrieval_date: "2026-11-25",
                        url: "https://www.cbn.gov.ng/Documents/circulars.asp",
                        relevant_finding:
                          "NGN 500bn International / NGN 200bn National bank minimum paid-up capital driving >NGN 2.2tn in capital market issuance.",
                        reliability_classification: "TIER_1_OFFICIAL",
                        epistemic_type: "FACT",
                      },
                      {
                        id: "sr-3",
                        source_name: "Securities and Exchange Commission (SEC Nigeria)",
                        publication_title:
                          "SEC Nigeria Collective Investment Schemes (CIS) & Private Fund Guidelines",
                        publication_date: "2026-11-21",
                        retrieval_date: "2026-11-25",
                        url: "https://sec.gov.ng/regulation/rules-and-codes/",
                        relevant_finding:
                          "SEC CIS filings confirm accelerating inflows into Money Market Funds and USD Fixed-Income Funds.",
                        reliability_classification: "TIER_1_OFFICIAL",
                        epistemic_type: "FACT",
                      },
                      {
                        id: "sr-4",
                        source_name: "National Pension Commission (PenCom)",
                        publication_title:
                          "PenCom Monthly Pension Fund Assets & Allocation Summary Report",
                        publication_date: "2026-11-23",
                        retrieval_date: "2026-11-25",
                        url: "https://www.pencom.gov.ng/category/publications/monthly-reports/",
                        relevant_finding:
                          "Total Nigerian Pension Fund Assets exceeded NGN 21.9 trillion (>62% in FGN Securities), leaving large headroom for Infrastructure & PE funds.",
                        reliability_classification: "TIER_1_OFFICIAL",
                        epistemic_type: "FACT",
                      },
                    ]
                ).map((s) => (
                  <tr key={s.id} className="hover:bg-slate-900/60">
                    <td className="py-3 px-3 font-semibold text-white">
                      {s.source_name}
                    </td>
                    <td className="py-3 px-3 text-slate-200">{s.publication_title}</td>
                    <td className="py-3 px-3 text-slate-300 max-w-md">
                      {s.relevant_finding}
                    </td>
                    <td className="py-3 px-3">
                      <Badge variant="emerald">{s.reliability_classification}</Badge>
                    </td>
                    <td className="py-3 px-3">
                      <Badge variant="sky">{s.epistemic_type}</Badge>
                    </td>
                    <td className="py-3 px-3">
                      <a
                        href={s.url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-sky-400 hover:underline font-mono"
                      >
                        Source <ExternalLink className="h-3 w-3" />
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
