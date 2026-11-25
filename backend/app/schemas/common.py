"""
Strict Pydantic v2 Structured Schemas for the 8 Specialized Agents,
the 11-Question Research Engine, Opportunity Radar, and API contracts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


# ------------------------------------------------------------------------------
# 1. Authentication & RBAC Schemas
# ------------------------------------------------------------------------------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: Dict[str, Any]


# ------------------------------------------------------------------------------
# 2. Section 5: 11-Question Research & Intelligence Engine Schema
# ------------------------------------------------------------------------------
class EpistemicBreakdownSchema(BaseModel):
    """Explicit separation of Facts, Estimates, Opinions, and AI-Generated Interpretations."""

    facts: List[str] = Field(default_factory=list)
    estimates: List[str] = Field(default_factory=list)
    opinions: List[str] = Field(default_factory=list)
    ai_interpretations: List[str] = Field(default_factory=list)


class ElevenQuestionDevelopmentSchema(BaseModel):
    """
    Mandatory 11-question deep analytical framework for every significant market,
    macroeconomic, competitive, or regulatory development (Section 5).
    """

    headline: str
    domain: str = Field(..., description="EQUITIES | FIXED_INCOME | FX | MACRO | COMMODITIES | COMPETITIVE | REGULATORY")
    market_region: str = Field(default="NIGERIA")
    event_date: str
    q1_what_happened: str
    q2_why_it_happened: str
    q3_what_caused_it: str
    q4_why_significant: str
    q5_who_benefits: List[str]
    q6_who_loses: List[str]
    q7_immediate_implications: str
    q8_long_term_implications: str
    q9_opportunities_created: str
    q10_risks_introduced: str
    q11_management_considerations: str
    quantitative_evidence: Dict[str, Any] = Field(default_factory=dict)
    epistemic_breakdown: EpistemicBreakdownSchema
    significance_score: float = Field(default=85.0, ge=0.0, le=100.0)
    source_register_ids: List[str] = Field(default_factory=list)


# ------------------------------------------------------------------------------
# 3. Section 6 & Agent 7: Investment & Strategic Opportunity Radar Schemas
# ------------------------------------------------------------------------------
class StrategicEvaluationTenCriteriaSchema(BaseModel):
    """Agent 7 (Strategic Intelligence Agent) 10-criterion business opportunity matrix."""

    market_size: str
    market_growth: str
    customer_demand: str
    competitive_intensity: str
    revenue_potential: str
    profitability: str
    regulatory_requirements: str
    capital_requirements: str
    execution_difficulty: str
    strategic_fit: str


class OpportunityRadarItemSchema(BaseModel):
    """
    Section 6 Investment Opportunity Radar & Agent 7 Strategic Business Opportunity record.
    """

    opportunity_class: str = Field(
        default="INVESTMENT_OPPORTUNITY",
        description="INVESTMENT_OPPORTUNITY | STRATEGIC_BUSINESS_OPPORTUNITY",
    )
    radar_category: str = Field(
        ...,
        description=(
            "ATTRACTIVE_FIXED_INCOME_YIELD | UNDERVALUED_EQUITY | EMERGING_SECTOR | "
            "NEW_FINANCIAL_PRODUCT | MARKET_INEFFICIENCY | DISTRESSED_ASSET | "
            "REGULATORY_OPPORTUNITY | UNDERSERVED_SEGMENT | NEW_BUSINESS_MODEL | AFRICAN_REPLICATION_PLAY"
        ),
    )
    target_business_line: str = Field(
        ...,
        description=(
            "ASSET_MANAGEMENT | INVESTMENT_BANKING | WEALTH_MANAGEMENT | FINANCIAL_ADVISORY | "
            "FINTECH | ALTERNATIVE_INVESTMENTS | CAPITAL_MARKET_SERVICES | INSTITUTIONAL_INVESTMENT"
        ),
    )
    title: str
    instrument_or_sector: str
    geography: str = "Nigeria"
    thesis: str
    supporting_quantitative_evidence: Dict[str, Any] = Field(default_factory=dict)
    assumptions: List[str] = Field(default_factory=list)
    risk_assessment: str

    # 7 Mandatory Ranking Dimensions (0 - 100)
    score_potential_return: float = Field(..., ge=0.0, le=100.0)
    score_risk_adjusted: float = Field(..., ge=0.0, le=100.0)
    score_market_attractiveness: float = Field(..., ge=0.0, le=100.0)
    score_evidence_quality: float = Field(..., ge=0.0, le=100.0)
    score_liquidity: float = Field(..., ge=0.0, le=100.0)
    score_regulatory_feasibility: float = Field(..., ge=0.0, le=100.0)
    time_horizon: str = "MEDIUM_TERM_6_18M"

    strategic_evaluation_matrix: Optional[StrategicEvaluationTenCriteriaSchema] = None
    composite_rank_score: float = Field(..., ge=0.0, le=100.0)
    status: str = "ACTIVE_HIGH_CONVICTION"
    source_register_ids: List[str] = Field(default_factory=list)


# ------------------------------------------------------------------------------
# 4. Final Objective: Five Core Strategic Questions Schema
# ------------------------------------------------------------------------------
class FiveStrategicQuestionsSchema(BaseModel):
    """Explicit executive answers to the 5 Core Strategic Questions."""

    q1_where_is_market_currently: str
    q2_what_is_changing_in_market: str
    q3_where_are_emerging_opportunities: str
    q4_what_are_risks_and_threats: str
    q5_what_strategic_actions_should_organisation_consider: List[str]
