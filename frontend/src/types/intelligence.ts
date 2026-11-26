/**
 * TypeScript Interfaces matching the FastAPI Pydantic v2 schemas.
 */

export interface FiveStrategicQuestions {
  q1_where_is_market_currently: string;
  q2_what_is_changing_in_market: string;
  q3_where_are_emerging_opportunities: string;
  q4_what_are_risks_and_threats: string;
  q5_what_strategic_actions_should_organisation_consider: string[];
}

export interface EpistemicBreakdown {
  facts: string[];
  estimates: string[];
  opinions: string[];
  ai_interpretations: string[];
}

export interface ElevenQuestionDevelopment {
  id?: string;
  headline: string;
  domain: string;
  market_region: string;
  event_date: string;
  q1_what_happened: string;
  q2_why_it_happened: string;
  q3_what_caused_it: string;
  q4_why_significant: string;
  q5_who_benefits: string[];
  q6_who_loses: string[];
  q7_immediate_implications: string;
  q8_long_term_implications: string;
  q9_opportunities_created: string;
  q10_risks_introduced: string;
  q11_management_considerations: string;
  quantitative_evidence: Record<string, number | string>;
  epistemic_breakdown: EpistemicBreakdown;
  significance_score: number;
  verification_status?: string;
  source_register_ids: string[];
}

export interface SymbolPerformanceMetrics {
  symbol: string;
  indicator_name?: string;
  asset_class?: string;
  market_region?: string;
  currency_or_unit?: string;
  as_of_date: string;
  latest_price: number;
  period_returns_pct: Record<string, number | null>;
  moving_averages: Record<string, number | null>;
  momentum_indicators: Record<string, number | null>;
  annualized_volatility_pct: number;
  rolling_30d_volatility_pct: number | null;
  downside_deviation_pct: number;
  max_drawdown_pct: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  calmar_ratio: number | null;
  parametric_var_95_pct: number;
  parametric_var_99_pct: number;
  historical_var_95_pct: number;
  historical_var_99_pct: number;
  observations_count: number;
  independent_check_passed: boolean;
}

export interface YieldCurveAnalytics {
  curve_name: string;
  observed_points: Array<{ tenor_years: number; yield_pct: number }>;
  nelson_siegel_params: Record<string, number>;
  fitted_standard_tenors: Record<string, number>;
  real_yields_fisher_pct: Record<string, number>;
  simple_real_spreads_pct: Record<string, number>;
  term_spreads_bps: Record<string, number>;
  curve_shape: string;
  average_nominal_yield_pct: number;
  average_real_yield_pct: number;
  inflation_benchmark_pct: number;
  fit_rmse_bps: number;
  independent_check_passed: boolean;
}

export interface BondRiskMetrics {
  clean_price: number;
  macaulay_duration_years: number;
  modified_duration_years: number;
  effective_convexity: number;
  dv01_per_100_par: number;
  price_change_plus_100bps_pct: number;
  price_change_minus_100bps_pct: number;
  independent_check_passed: boolean;
}

export interface OpportunityRadarItem {
  id: string;
  opportunity_class: "INVESTMENT_OPPORTUNITY" | "STRATEGIC_BUSINESS_OPPORTUNITY" | string;
  radar_category: string;
  target_business_line: string;
  title: string;
  instrument_or_sector: string;
  geography?: string;
  thesis: string;
  supporting_quantitative_evidence?: Record<string, number | string>;
  assumptions?: string[];
  risk_assessment: string;
  composite_rank_score?: number;
  score_evidence_quality?: number;
  scores?: {
    potential_return: number;
    risk_adjusted: number;
    market_attractiveness: number;
    evidence_quality: number;
    liquidity: number;
    regulatory_feasibility: number;
    composite_rank_score: number;
  };
  time_horizon: string;
  strategic_evaluation_matrix?: Record<string, string>;
  status: string;
  source_register_ids?: string[];
  identified_at?: string;
}

export interface CompetitorProfile {
  id: string;
  name: string;
  category: string;
  tier: string;
  headquarters: string;
  key_products: string[];
  aum_or_capital_estimate: string;
  competitive_strengths: string[];
  vulnerabilities: string[];
  updated_at: string;
}

export interface CompetitorEvent {
  id: string;
  competitor_id: string;
  competitor_name: string;
  competitor_category: string;
  event_type: string;
  event_date: string;
  title: string;
  summary: string;
  what_they_are_doing_differently: string;
  implications_for_our_business: string;
  recommended_counter_strategy: string;
  threat_level: string;
  source_register_id: string;
}

export interface RegulatoryEvent {
  id: string;
  regulator_code: string;
  regulator_name: string;
  reference_number: string;
  title: string;
  issued_date: string;
  policy_summary: string;
  compliance_implications: string;
  capital_or_operational_impact: string;
  business_opportunities_created: string;
  affected_segments: string[];
  severity: string;
  is_official_publication: boolean;
  source_register_id: string;
}

export interface SourceRegisterEntry {
  id: string;
  source_id?: string;
  source_name: string;
  publication_title: string;
  publication_date: string;
  retrieval_date: string;
  url: string;
  relevant_finding: string;
  reliability_classification: string;
  epistemic_type: string;
  verification_status?: string;
}

export interface WeeklyReportSummary {
  id: string;
  report_code: string;
  title: string;
  period_start_friday: string;
  period_end_friday: string;
  executive_summary: string;
  five_strategic_questions?: FiveStrategicQuestions;
  sections_count?: number;
  sections?: Record<string, any>;
  pdf_file_path?: string | null;
  excel_file_path?: string | null;
  google_drive_pdf_id?: string | null;
  google_drive_excel_id?: string | null;
  email_delivery_status?: string;
  published_at: string;
}

export interface AssistantAskResponse {
  question: string;
  answer_markdown: string;
  referenced_report_code: string;
  retrieved_evidence_chunks: Array<{
    chunk_id: string;
    similarity_score: number;
    text: string;
    metadata: Record<string, any>;
  }>;
  citations: SourceRegisterEntry[];
  generated_at_utc: string;
}
