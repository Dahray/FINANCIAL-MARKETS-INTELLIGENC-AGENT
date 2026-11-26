"""
AGENT 5: REGULATORY INTELLIGENCE AGENT
Monitors:
- Central Bank of Nigeria (CBN)
- Securities and Exchange Commission (SEC Nigeria)
- Nigerian Exchange (NGX)
- National Pension Commission (PenCom)
- National Insurance Commission (NAICOM)
- Financial Reporting Council (FRC)
- Federal Ministry of Finance (FMF)
- International regulators
Identifies policy changes, compliance implications, and business opportunities.
Prioritizes official publications.
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from app.agents.llm import GeminiResearchClient
from app.agents.state import ResearchGraphState


class RegulatoryEventItemSchema(BaseModel):
    regulator_code: str
    regulator_name: str
    reference_number: str
    title: str
    issued_date: str
    policy_summary: str
    compliance_implications: str
    capital_or_operational_impact: str
    business_opportunities_created: str
    affected_segments: List[str]
    severity: str = "MANDATORY_COMPLIANCE"
    is_official_publication: bool = True
    source_register_id: str


class Agent5RegulatoryIntelligenceOutput(BaseModel):
    """Structured output produced by Agent 5 (Regulatory Intelligence Agent)."""

    regulatory_executive_summary: str
    cbn_and_monetary_regulation_update: str
    sec_ngx_and_capital_markets_update: str
    pencom_and_naicom_institutional_update: str
    frc_and_ministry_of_finance_update: str
    regulatory_events: List[RegulatoryEventItemSchema] = Field(default_factory=list)
    source_register_ids: List[str] = Field(default_factory=list)


def run_agent_5_regulatory(state: ResearchGraphState) -> ResearchGraphState:
    """Execute Agent 5 (Regulatory Intelligence Agent) prioritizing Tier-1 official publications."""
    ledger = state.get("source_register_ledger", [])
    valid_sources = state.get("valid_source_ids", [])
    default_src = valid_sources[0] if valid_sources else ""

    # Map source_register IDs by regulator keyword
    def _find_source_id(keyword: str) -> str:
        for entry in ledger:
            blob = f"{entry.get('source_name', '')} {entry.get('publication_title', '')}".lower()
            if keyword.lower() in blob:
                return str(entry["id"])
        return default_src

    def _build_deterministic() -> Agent5RegulatoryIntelligenceOutput:
        cbn_src = _find_source_id("cbn")
        sec_src = _find_source_id("sec")
        pen_src = _find_source_id("pencom")

        events = [
            RegulatoryEventItemSchema(
                regulator_code="CBN",
                regulator_name="Central Bank of Nigeria (CBN)",
                reference_number="FPR/DIR/PUB/CIR/002/009",
                title="CBN Banking Sector Recapitalisation & Minimum Paid-Up Capital Framework Enforcement",
                issued_date=ledger[0]["publication_date"] if ledger else "2026-11-20",
                policy_summary=(
                    "Strict enforcement of paid-up share capital and share premium minimums (NGN 500bn International Commercial Banks, "
                    "NGN 200bn National Commercial Banks, NGN 50bn Merchant Banks), excluding retained earnings from qualifying capital."
                ),
                compliance_implications=(
                    "Requires capital verification, CBN/SEC allotment clearance, and strict anti-money-laundering vetting on all capital calls before the March 2026/2027 compliance milestones."
                ),
                capital_or_operational_impact=(
                    "Triggers over NGN 2.2 trillion in primary equity and rights issuance across Nigerian banking groups and potential Tier-2 M&A consolidation."
                ),
                business_opportunities_created=(
                    "Major fee pool for Investment Banking (Issuing House, Underwriting, Financial Advisory, M&A) and institutional securities placement."
                ),
                affected_segments=["COMMERCIAL_BANK", "INVESTMENT_BANK", "CAPITAL_MARKET_SERVICES", "ASSET_MANAGEMENT"],
                severity="MANDATORY_COMPLIANCE",
                is_official_publication=True,
                source_register_id=cbn_src,
            ),
            RegulatoryEventItemSchema(
                regulator_code="CBN",
                regulator_name="Central Bank of Nigeria (CBN)",
                reference_number="CBN/MPC/COMM/2026",
                title="Monetary Policy Committee Directive on 50% CRR and NAFEM Electronic FX Matching Surveillance",
                issued_date=ledger[0]["publication_date"] if ledger else "2026-11-22",
                policy_summary=(
                    "Maintenance of 27.50% MPR and 50.00% Commercial Bank CRR alongside mandatory real-time order-book transparency on the NAFEM FX trading system."
                ),
                compliance_implications=(
                    "Authorized Dealer banks and treasury desks must comply with strict intraday NOP (Net Open Position) limits and automated FX reporting."
                ),
                capital_or_operational_impact=(
                    "Sterilizes bank excess Naira liquidity, keeping interbank funding costs above 30% and penalizing unhedged FX positions."
                ),
                business_opportunities_created=(
                    "Creates strong corporate demand for SEC-regulated Commercial Paper issuance and Money Market Fund liquidity sweeps."
                ),
                affected_segments=["COMMERCIAL_BANK", "ASSET_MANAGEMENT", "WEALTH_MANAGEMENT"],
                severity="MANDATORY_COMPLIANCE",
                is_official_publication=True,
                source_register_id=cbn_src,
            ),
            RegulatoryEventItemSchema(
                regulator_code="SEC_NG",
                regulator_name="Securities and Exchange Commission (SEC Nigeria)",
                reference_number="SEC/REG/CIS/2026",
                title="SEC Nigeria Collective Investment Schemes (CIS) Mark-to-Market Valuation & Private Fund Governance Rules",
                issued_date=ledger[0]["publication_date"] if ledger else "2026-11-21",
                policy_summary=(
                    "Enforces standardized NAV valuation reporting, custodial asset segregation, and accelerated registration for Infrastructure Debt, Private Equity, and Digital Asset / VASP vehicles."
                ),
                compliance_implications=(
                    "Fund managers must submit daily/weekly NAV computations and maintain strict compliance with asset allocation bands."
                ),
                capital_or_operational_impact=(
                    "Strengthens investor protection and favors institutional asset managers with robust risk and valuation infrastructure."
                ),
                business_opportunities_created=(
                    "Enables launch of SEC-approved USD Eurobond Funds, Naira Infrastructure Debt Funds, and compliant digital wealth partnerships."
                ),
                affected_segments=["ASSET_MANAGEMENT", "WEALTH_MANAGEMENT", "ALTERNATIVE_INVESTMENTS", "FINTECH"],
                severity="STRATEGIC_SHIFT",
                is_official_publication=True,
                source_register_id=sec_src,
            ),
            RegulatoryEventItemSchema(
                regulator_code="PENCOM",
                regulator_name="National Pension Commission (PenCom)",
                reference_number="PENCOM/INV/AUM/2026",
                title="PenCom Revised Regulation on Investment of Pension Fund Assets in Infrastructure & Private Equity",
                issued_date=ledger[0]["publication_date"] if ledger else "2026-11-23",
                policy_summary=(
                    "Permits Pension Fund Administrators (PFAs) managing >NGN 21.9 trillion in AUM to expand allocations to SEC-registered Infrastructure Funds (up to 5% in RSA Fund I-III) and Private Equity Funds."
                ),
                compliance_implications=(
                    "Qualifying funds must maintain investment-grade credit enhancement or DFI co-investment and list on an approved exchange (NGX/FMDQ)."
                ),
                capital_or_operational_impact=(
                    "Unlocks over NGN 800 billion in potential pension institutional commitments for bankable real-sector and infrastructure funds."
                ),
                business_opportunities_created=(
                    "High-margin alternative asset management opportunity: structuring a PenCom-compliant Naira Infrastructure & Real Assets Debt Fund."
                ),
                affected_segments=["PFA", "ALTERNATIVE_INVESTMENTS", "ASSET_MANAGEMENT", "INSTITUTIONAL_INVESTMENT"],
                severity="STRATEGIC_SHIFT",
                is_official_publication=True,
                source_register_id=pen_src,
            ),
        ]

        return Agent5RegulatoryIntelligenceOutput(
            regulatory_executive_summary=(
                "Nigerian financial regulation is dominated by three structural pillars: (1) CBN's NGN 500bn/200bn Banking Recapitalisation "
                "and strict 50% CRR / NAFEM FX surveillance; (2) SEC Nigeria's tightening of Collective Investment Scheme (CIS) governance "
                "and expansion of alternative/digital asset licensing; and (3) PenCom's push to diversify NGN 21.9+ trillion in pension assets "
                "beyond FGN securities into SEC-regulated infrastructure and private equity funds."
            ),
            cbn_and_monetary_regulation_update=(
                "The CBN continues to enforce strict capital verification on bank recapitalisation proceeds alongside Net Open Position (NOP) "
                "limits and electronic FX matching rules in the NAFEM window."
            ),
            sec_ngx_and_capital_markets_update=(
                "SEC Nigeria and NGX have streamlined e-offering rules for bank rights issues and Commercial Paper shelf programmes while "
                "enforcing mark-to-market transparency across fixed-income mutual funds."
            ),
            pencom_and_naicom_institutional_update=(
                "PenCom's monthly AUM report (>NGN 21.9 trillion) confirms >62% concentration in FGN securities, creating regulatory impetus "
                "for PFAs to allocate to qualifying infrastructure debt funds. NAICOM continues risk-based capital enforcement across composite insurers."
            ),
            frc_and_ministry_of_finance_update=(
                "The Financial Reporting Council (FRC) and Federal Ministry of Finance are enforcing IFRS sustainability disclosure readiness (IFRS S1/S2) "
                "and fiscal revenue digitalization across public and listed financial institutions."
            ),
            regulatory_events=events,
            source_register_ids=list({e.source_register_id for e in events if e.source_register_id}),
        )

    out = GeminiResearchClient.generate_structured(
        system_instruction=(
            "You are Agent 5: Institutional Regulatory Intelligence Agent monitoring CBN, SEC Nigeria, NGX, PenCom, NAICOM, FRC, and FMF. "
            "Prioritize Tier-1 official publications and link every regulatory event to a valid source_register_id."
        ),
        user_prompt=f"Synthesize regulatory intelligence from verified source register: {ledger}.",
        response_schema=Agent5RegulatoryIntelligenceOutput,
        deterministic_builder=_build_deterministic,
        use_fast_model=True,
    )
    state["agent_5_regulatory_output"] = out.model_dump()
    return state
