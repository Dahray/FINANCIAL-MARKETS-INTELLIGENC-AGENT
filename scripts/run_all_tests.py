"""
Unified Master QA & Verification Runner for the Financial Markets Intelligence Platform.
Executes all Phase 2, Phase 3, Phase 4, Phase 5, and Phase 6 automated test suites.
"""

from __future__ import annotations

from pathlib import Path
import sys
import time

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from tests.unit.test_phase2_quant_and_ingestion import (
    test_all_18_orm_tables_registered_and_created,
    test_data_quality_gate_deduplication_and_outlier_flagging,
    test_deterministic_quantitative_engine_calculations,
    test_fastapi_phase2_endpoints,
    test_financial_statement_extractor_never_fabricates_missing_metrics,
    test_security_password_hashing_and_prompt_injection_sanitizer,
)
from tests.unit.test_phase3_multi_agent_system import (
    test_competitors_regulatory_and_executive_ai_assistant,
    test_eight_agent_research_cycle_and_16_section_report,
    test_overview_11_question_developments_and_opportunity_radar,
)
from tests.unit.test_phase4_dashboard_integration import (
    test_all_8_mandatory_dashboard_pages_and_charts_exist,
    test_frontend_to_backend_api_contracts,
)
from tests.unit.test_phase5_reporting_and_automation import (
    test_n8n_workflows_webhooks_and_worker,
    test_pdf_and_excel_generation_and_download_endpoints,
)
from tests.integration.test_phase6_comprehensive_e2e_and_security import (
    test_1_financial_calculations_and_forecast_backtesting,
    test_2_data_ingestion_and_quality_gate,
    test_3_eight_specialized_agent_outputs_and_evidence_gate,
    test_4_citations_and_source_register_traceability,
    test_5_automation_webhooks_and_secret_authentication,
    test_6_report_generation_pdf_and_excel_integrity,
    test_7_application_security_rbac_and_zero_frontend_secret_leakage,
)
from tests.integration.test_stage8_verification_and_research_memory import (
    run_stage8_verification_suite,
)
from tests.integration.test_stage9_institutional_weekly_research import (
    run_stage9_institutional_research_suite,
)


def main() -> None:
    suites = [
        ("Phase 2.1", test_all_18_orm_tables_registered_and_created),
        ("Phase 2.2", test_security_password_hashing_and_prompt_injection_sanitizer),
        ("Phase 2.3", test_data_quality_gate_deduplication_and_outlier_flagging),
        ("Phase 2.4", test_financial_statement_extractor_never_fabricates_missing_metrics),
        ("Phase 2.5", test_deterministic_quantitative_engine_calculations),
        ("Phase 2.6", test_fastapi_phase2_endpoints),
        ("Phase 3.1", test_eight_agent_research_cycle_and_16_section_report),
        ("Phase 3.2", test_overview_11_question_developments_and_opportunity_radar),
        ("Phase 3.3", test_competitors_regulatory_and_executive_ai_assistant),
        ("Phase 4.1", test_all_8_mandatory_dashboard_pages_and_charts_exist),
        ("Phase 4.2", test_frontend_to_backend_api_contracts),
        ("Phase 5.1", test_pdf_and_excel_generation_and_download_endpoints),
        ("Phase 5.2", test_n8n_workflows_webhooks_and_worker),
        ("Phase 6.1", test_1_financial_calculations_and_forecast_backtesting),
        ("Phase 6.2", test_2_data_ingestion_and_quality_gate),
        ("Phase 6.3", test_3_eight_specialized_agent_outputs_and_evidence_gate),
        ("Phase 6.4", test_4_citations_and_source_register_traceability),
        ("Phase 6.5", test_5_automation_webhooks_and_secret_authentication),
        ("Phase 6.6", test_6_report_generation_pdf_and_excel_integrity),
        ("Phase 6.7", test_7_application_security_rbac_and_zero_frontend_secret_leakage),
        ("Stage 8", run_stage8_verification_suite),
        ("Stage 9", run_stage9_institutional_research_suite),
    ]


    start_t = time.time()
    print("=" * 78)
    print("SOHCAHTOA FMIP — MASTER END-TO-END & SECURITY VERIFICATION RUNNER")
    print("=" * 78)
    for phase_tag, fn in suites:
        t0 = time.time()
        fn()
        elapsed = (time.time() - t0) * 1000.0
        print(f"[PASS] [{phase_tag}] {fn.__name__} ({elapsed:.0f} ms)")

    total_s = time.time() - start_t
    print("=" * 78)
    print(f"ALL {len(suites)} INSTITUTIONAL VERIFICATION SUITES PASSED IN {total_s:.2f}s!")
    print("=" * 78)


if __name__ == "__main__":
    main()
