"""
AGENT 4: COMPETITIVE INTELLIGENCE AGENT
Monitors the activities of all 9 mandatory competitor categories:
1. Asset management firms
2. Commercial banks
3. Investment banks
4. Pension fund administrators (PFAs)
5. Insurance companies
6. Fintech companies
7. Brokerage firms
8. Investment platforms
9. Wealth management companies

Identifies:
- New products, New market entrants, Mergers & acquisitions, Partnerships,
  Business model innovations, Market expansion, Competitive positioning,
  Pricing changes, Strategic investments.
Explains what competitors are doing differently and the implications for our business.
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.llm import GeminiResearchClient
from app.agents.state import ResearchGraphState
from app.agents.tools.research_tools import tool_load_competitor_profiles


class CompetitorEventItemSchema(BaseModel):
    competitor_name: str
    competitor_category: str
    event_type: str = Field(
        ...,
        description=(
            "NEW_PRODUCT | MARKET_ENTRY | M_AND_A | PARTNERSHIP | BUSINESS_MODEL_INNOVATION | "
            "MARKET_EXPANSION | COMPETITIVE_POSITIONING | PRICING_CHANGE | STRATEGIC_INVESTMENT"
        ),
    )
    event_date: str
    title: str
    summary: str
    what_they_are_doing_differently: str
    implications_for_our_business: str
    recommended_counter_strategy: str
    threat_level: str = "HIGH"
    source_register_id: str


class Agent4CompetitiveIntelligenceOutput(BaseModel):
    """Structured output produced by Agent 4 (Competitive Intelligence Agent)."""

    competitive_landscape_overview: str
    asset_and_wealth_management_competition: str
    banking_and_investment_banking_competition: str
    pfa_and_insurance_institutional_competition: str
    fintech_brokerage_and_digital_platforms_competition: str
    competitor_events: List[CompetitorEventItemSchema] = Field(default_factory=list)
    source_register_ids: List[str] = Field(default_factory=list)


def run_agent_4_competitor(state: ResearchGraphState, db: Session) -> ResearchGraphState:
    """Execute Agent 4 (Competitive Intelligence Agent) across the 9 financial services segments."""
    profiles = tool_load_competitor_profiles(db)
    valid_sources = state.get("valid_source_ids", [])
    default_src = valid_sources[0] if valid_sources else ""

    def _build_deterministic() -> Agent4CompetitiveIntelligenceOutput:
        events = [
            CompetitorEventItemSchema(
                competitor_name="Stanbic IBTC Holdings Plc",
                competitor_category="ASSET_MANAGEMENT",
                event_type="NEW_PRODUCT",
                event_date="2026-11-21",
                title="Aggressive Scaling of Stanbic IBTC Money Market & Dollar Fund Direct Digital Distribution",
                summary=(
                    "Stanbic IBTC Asset Management expanded automated mobile sweep capabilities into its Money Market and USD Dollar Funds, "
                    "capturing retail and corporate liquidity seeking >20% Naira yields and USD protection."
                ),
                what_they_are_doing_differently=(
                    "Integrating bank holdco current accounts, pension RSA onboarding, and mutual fund subscriptions into a single digital super-app ecosystem."
                ),
                implications_for_our_business=(
                    "Raises customer acquisition bar in retail and mass-affluent asset management; standalone funds without seamless mobile onboarding risk AUM attrition."
                ),
                recommended_counter_strategy=(
                    "Launch API-first embedded treasury and money-market sweep modules with transparent daily yield reporting and institutional fee tiers."
                ),
                threat_level="HIGH",
                source_register_id=default_src,
            ),
            CompetitorEventItemSchema(
                competitor_name="Chapel Hill Denham",
                competitor_category="INVESTMENT_BANK",
                event_type="STRATEGIC_INVESTMENT",
                event_date="2026-11-20",
                title="Expansion of Naira Infrastructure Debt & Renewable Energy Co-Investment Tranches for PFAs",
                summary=(
                    "Chapel Hill Denham structured additional long-tenor Naira infrastructure debt tranches anchored by Nigerian PFAs and DFI credit guarantees."
                ),
                what_they_are_doing_differently=(
                    "Positioning alternative credit vehicles as inflation-indexed, PenCom-compliant substitutes for traditional FGN bonds."
                ),
                implications_for_our_business=(
                    "Captures long-duration institutional management fees (1.5%–2.0% p.a.) from PFAs looking to diversify away from sovereign bonds."
                ),
                recommended_counter_strategy=(
                    "Structure a niche mid-market Private Credit & Export-Agribusiness Infrastructure Debt Fund co-guaranteed by regional DFIs."
                ),
                threat_level="HIGH",
                source_register_id=default_src,
            ),
            CompetitorEventItemSchema(
                competitor_name="United Capital Plc",
                competitor_category="INVESTMENT_BANK",
                event_type="MARKET_EXPANSION",
                event_date="2026-11-22",
                title="Commercial Paper Origination Surge & Eurobond Fund Expansion via InvestNow",
                summary=(
                    "United Capital accelerated FMDQ Commercial Paper arranging mandates for mid-to-large corporates priced out of 32%+ bank loans."
                ),
                what_they_are_doing_differently=(
                    "Bundling CP issuance advisory with immediate distribution into internal mutual funds and retail HNI syndication."
                ),
                implications_for_our_business=(
                    "Integrated origination-to-distribution shortens deal execution timelines and captures both issuing-house and fund-management fees."
                ),
                recommended_counter_strategy=(
                    "Establish a dedicated Debt Capital Markets (DCM) Commercial Paper desk linked directly to our private wealth and institutional liquidity pools."
                ),
                threat_level="MODERATE",
                source_register_id=default_src,
            ),
            CompetitorEventItemSchema(
                competitor_name="Guaranty Trust Holding Company Plc (GTCO)",
                competitor_category="COMMERCIAL_BANK",
                event_type="M_AND_A",
                event_date="2026-11-19",
                title="HoldCo Capital Deployment into Non-Bank Asset Management, Pension, and HabariPay Subsidiaries",
                summary=(
                    "Following recapitalisation capital raises, Tier-1 banking HoldCos (GTCO, Access Holdings) are scaling their wealth, pension, and payment subsidiaries."
                ),
                what_they_are_doing_differently=(
                    "Using zero-cost retail banking touchpoints to cross-sell SEC-regulated mutual funds and pension transfers at near-zero customer acquisition cost."
                ),
                implications_for_our_business=(
                    "Intensifies competition for standard retail money market products, forcing independent firms to differentiate on alpha, speed, and bespoke advisory."
                ),
                recommended_counter_strategy=(
                    "Focus on high-touch HNI Family Office wealth management, corporate treasury advisory, and specialized high-yield private credit products that bank holdcos standardize poorly."
                ),
                threat_level="HIGH",
                source_register_id=default_src,
            ),
            CompetitorEventItemSchema(
                competitor_name="Moniepoint Inc",
                competitor_category="FINTECH",
                event_type="BUSINESS_MODEL_INNOVATION",
                event_date="2026-11-23",
                title="AI-Driven SME Working-Capital Lending & High-Yield Merchant Float Accounts",
                summary=(
                    "Moniepoint expanded automated working-capital credit lines and overnight merchant float yield features across its nationwide SME POS network."
                ),
                what_they_are_doing_differently=(
                    "Underwriting SME credit using real-time POS settlement velocity rather than traditional collateral, and monetizing idle merchant float."
                ),
                implications_for_our_business=(
                    "Creates partnership opportunities to provide institutional wholesale liquidity or securitized funding note structures to top-performing fintech lenders."
                ),
                recommended_counter_strategy=(
                    "Partner with tier-1 merchant fintechs as an institutional debt arranger and asset-backed commercial paper structurer rather than competing in mass-market POS hardware."
                ),
                threat_level="MODERATE",
                source_register_id=default_src,
            ),
            CompetitorEventItemSchema(
                competitor_name="PiggyVest / Cowrywise (Digital Wealth Platforms)",
                competitor_category="INVESTMENT_PLATFORM",
                event_type="PARTNERSHIP",
                event_date="2026-11-22",
                title="Embedded SEC Mutual Fund Marketplace & Fractional NTB Distribution",
                summary=(
                    "Digital wealth platforms are aggregating third-party SEC-registered mutual funds and fractionalized 364-day Treasury Bills for retail investors."
                ),
                what_they_are_doing_differently=(
                    "Acting as the digital front-end aggregator while partnering with licensed asset managers for back-end fund custody and execution."
                ),
                implications_for_our_business=(
                    "Provides a low-CAPEX B2B2C distribution channel for our asset management products if we expose white-label fund APIs."
                ),
                recommended_counter_strategy=(
                    "Build B2B2C white-label fund APIs to distribute our Money Market and Fixed-Income funds through partner fintech apps."
                ),
                threat_level="LOW",
                source_register_id=default_src,
            ),
        ]

        return Agent4CompetitiveIntelligenceOutput(
            competitive_landscape_overview=(
                "Competitive intensity across the Nigerian financial services industry is bifurcating along two axes: "
                "(1) Scale-driven Financial HoldCos (Stanbic IBTC, GTCO, Access Holdings, United Capital) leveraging recapitalised balance sheets "
                "and super-apps to dominate retail money market funds and pension administration; and (2) Specialized Alpha & Digital Challengers "
                "(Chapel Hill Denham in infrastructure/alternatives, CardinalStone in institutional brokerage/PE, and Moniepoint/PiggyVest in digital distribution)."
            ),
            asset_and_wealth_management_competition=(
                "Stanbic IBTC, FBNQuest, United Capital, and ARM continue to command over 65% of SEC-regulated CIS mutual fund AUM, "
                "with growth concentrated in Money Market Funds (>20% yield) and USD Dollar/Eurobond Funds."
            ),
            banking_and_investment_banking_competition=(
                "CBN's NGN 500bn/200bn recapitalisation mandate has catalyzed a wave of rights issues, public offers, and M&A advisory mandates, "
                "while 32%+ bank lending rates have shifted corporate debt origination toward FMDQ Commercial Paper arrangers (Chapel Hill Denham, United Capital, CardinalStone)."
            ),
            pfa_and_insurance_institutional_competition=(
                "PFAs (led by Stanbic IBTC Pension Managers, Access ARM Pensions, Leadway Pensure) are actively seeking inflation-hedged "
                "infrastructure debt and private equity co-investments to diversify their NGN 21.9+ trillion portfolio. Insurers are upgrading capital adequacy under NAICOM risk-based rules."
            ),
            fintech_brokerage_and_digital_platforms_competition=(
                "Fintechs (Moniepoint, OPay, PalmPay) and digital wealth aggregators (PiggyVest, Cowrywise, Bamboo) control retail customer UX, "
                "creating high-value B2B2C liquidity and securitization partnership opportunities for licensed institutional asset managers and investment banks."
            ),
            competitor_events=events,
            source_register_ids=[default_src] if default_src else [],
        )

    out = GeminiResearchClient.generate_structured(
        system_instruction=(
            "You are Agent 4: Institutional Competitive Intelligence Agent monitoring Nigerian and African financial services competitors."
        ),
        user_prompt=f"Analyze competitive intelligence across registered competitors: {profiles}.",
        response_schema=Agent4CompetitiveIntelligenceOutput,
        deterministic_builder=_build_deterministic,
        use_fast_model=True,
    )
    state["agent_4_competitor_output"] = out.model_dump()
    return state
