"""Typed LangGraph State shared across all 8 specialized financial research agents."""

from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class ResearchGraphState(TypedDict, total=False):
    """
    Shared state passed between nodes in the FMIP LangGraph Supervisor-Editor state machine.
    """

    run_id: str
    run_type: str
    period_start_iso: str
    period_end_iso: str

    # Raw verified database snapshots & valid citation registry
    source_register_ledger: List[Dict[str, Any]]
    valid_source_ids: List[str]

    # Immutable Deterministic Python Outputs from Agent 6 (Quantitative Analysis Agent)
    agent_6_quant_output: Dict[str, Any]

    # Domain Agent Outputs (Agents 1, 2, 3, 4, 5, 7)
    agent_1_market_output: Dict[str, Any]
    agent_2_macro_output: Dict[str, Any]
    agent_3_investment_output: Dict[str, Any]
    agent_4_competitor_output: Dict[str, Any]
    agent_5_regulatory_output: Dict[str, Any]
    agent_7_strategic_output: Dict[str, Any]

    # Consolidated Developments & Opportunity Radar Items
    developments_11q: List[Dict[str, Any]]
    opportunity_radar_items: List[Dict[str, Any]]

    # Agent 8 (Chief Research Editor) Quality Gate & Final 16-Section Report
    revision_count: int
    max_revisions: int
    editor_feedback: List[str]
    editor_approved: bool
    agent_8_editorial_review: Dict[str, Any]
    final_weekly_report: Dict[str, Any]
