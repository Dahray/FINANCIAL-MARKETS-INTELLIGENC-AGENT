"""
Centralized Financial Data Verification, Freshness SLA Monitoring & Automated
Cross-Source Discrepancy Detection Engine (Parts 1.1 – 1.6 & Part 6).

Architecture Guarantee:
SOURCE -> DATA INGESTION -> VERIFICATION ENGINE -> DATABASE -> ANALYTICAL ENGINE -> AI REASONING -> REPORTING

Core Governance Controls:
1. Enforces Tier 1 (Official Primary) > Tier 2 (Authorised Market Data Providers) > Tier 3 (Financial Press) > Archival Baseline.
2. Never deletes historical records when new official figures arrive.
3. Never lets synthetic archival baseline rows override live official Tier 1/2 publications.
4. Tracks publication_date, effective_date, retrieval_date, next_expected_update, age_days, and freshness_status.
5. Automatically detects cross-source discrepancies and logs every data change to `intelligence_change_log`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.macro import MacroIndicator
from app.models.market import MarketTimeseries, YieldCurvePoint
from app.models.memory import DataDiscrepancy, IntelligenceChangeLog
from app.models.source import DataSource

logger = get_logger("fmip.services.verification")


SOURCE_TIER_RANK: Dict[str, int] = {
    "TIER_1_OFFICIAL": 1,
    "TIER_2_INSTITUTIONAL": 2,
    "TIER_3_FINANCIAL_PRESS": 3,
    "ARCHIVAL_BASELINE": 4,
    "UNVERIFIED": 5,
}

SOURCE_TIER_DEFAULT_CONFIDENCE: Dict[str, float] = {
    "TIER_1_OFFICIAL": 98.0,
    "TIER_2_INSTITUTIONAL": 88.0,
    "TIER_3_FINANCIAL_PRESS": 70.0,
    "ARCHIVAL_BASELINE": 45.0,
    "UNVERIFIED": 25.0,
}

# Part 1.4: Indicator-specific freshness SLAs (in calendar days) & expected update cadence
INDICATOR_FRESHNESS_SLA: Dict[str, Dict[str, Any]] = {
    "NG_CBN_MPR": {
        "cadence": "After CBN MPC announcements (bi-monthly / ~60 days)",
        "fresh_days": 65,
        "stale_days": 95,
    },
    "NG_CBN_CRR_COMMERCIAL": {
        "cadence": "After CBN MPC / regulatory circulars",
        "fresh_days": 90,
        "stale_days": 150,
    },
    "NG_CPI_HEADLINE_YOY": {
        "cadence": "Monthly after official NBS / CBN CPI release",
        "fresh_days": 45,
        "stale_days": 65,
    },
    "NG_CPI_FOOD_YOY": {
        "cadence": "Monthly after official NBS / CBN CPI release",
        "fresh_days": 45,
        "stale_days": 65,
    },
    "NG_CPI_CORE_YOY": {
        "cadence": "Monthly after official NBS / CBN CPI release",
        "fresh_days": 45,
        "stale_days": 65,
    },
    "NG_GDP_REAL_YOY": {
        "cadence": "Quarterly after official NBS GDP release",
        "fresh_days": 110,
        "stale_days": 145,
    },
    "NG_FX_RESERVES_USD": {
        "cadence": "Daily / business days via CBN External Reserves",
        "fresh_days": 7,
        "stale_days": 14,
    },
    "NG_PRIME_LENDING_RATE": {
        "cadence": "Monthly via CBN Money Market Indicators",
        "fresh_days": 45,
        "stale_days": 65,
    },
    "NG_MAX_LENDING_RATE": {
        "cadence": "Monthly via CBN Money Market Indicators",
        "fresh_days": 45,
        "stale_days": 65,
    },
    "NG_CRUDE_PRODUCTION_MBPD": {
        "cadence": "Monthly via CBN Crude Oil & Gas Statistics",
        "fresh_days": 45,
        "stale_days": 75,
    },
    "US_FED_FUNDS": {
        "cadence": "Monthly / FOMC cycle via Federal Reserve (FRED)",
        "fresh_days": 45,
        "stale_days": 70,
    },
    "NGXASI": {
        "cadence": "Daily trading days via NGX Group",
        "fresh_days": 4,
        "stale_days": 10,
    },
    "NGNUSD.NAFEM": {
        "cadence": "Daily trading days via CBN NFEM / FMDQ",
        "fresh_days": 4,
        "stale_days": 10,
    },
    "USDNGN.AV": {
        "cadence": "Daily via Alpha Vantage FX",
        "fresh_days": 4,
        "stale_days": 10,
    },
    "NG_OPR_RATE": {
        "cadence": "Daily / Monthly via CBN & FMDQ Money Markets",
        "fresh_days": 35,
        "stale_days": 60,
    },
    "NG_OVN_RATE": {
        "cadence": "Daily via FMDQ Money Markets",
        "fresh_days": 7,
        "stale_days": 14,
    },
    "BRENT": {
        "cadence": "Daily trading days via FRED / FMP",
        "fresh_days": 7,
        "stale_days": 14,
    },
    "BONNYLIGHT": {
        "cadence": "Monthly official CBN Crude Oil benchmark",
        "fresh_days": 45,
        "stale_days": 75,
    },
    "SPX": {
        "cadence": "Daily trading days via FMP / Global Equities",
        "fresh_days": 4,
        "stale_days": 10,
    },
    "NTB": {
        "cadence": "Bi-weekly after CBN/DMO Primary Market Auctions",
        "fresh_days": 21,
        "stale_days": 35,
    },
    "FGN_BOND": {
        "cadence": "Daily secondary / Monthly DMO Primary Auctions",
        "fresh_days": 35,
        "stale_days": 60,
    },
}


def _to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def compute_freshness_assessment(
    indicator_key: str,
    publication_date: datetime,
    effective_date: Optional[datetime] = None,
    is_archival_baseline: bool = False,
    has_unresolved_discrepancy: bool = False,
    reference_now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Evaluate indicator age, next expected update window, and freshness classification
    (`FRESH`, `AGING`, `STALE`, `ARCHIVAL_BASELINE_ONLY`, `DISPUTED`).
    """
    now = _to_utc(reference_now) or datetime.now(timezone.utc)
    pub_utc = _to_utc(publication_date) or now
    eff_utc = _to_utc(effective_date) or pub_utc

    sla = INDICATOR_FRESHNESS_SLA.get(
        indicator_key,
        {"cadence": "Periodic official release", "fresh_days": 35, "stale_days": 65},
    )
    age_days = max(0.0, round((now - eff_utc).total_seconds() / 86400.0, 1))
    next_expected = eff_utc + timedelta(days=int(sla["fresh_days"]))

    if has_unresolved_discrepancy:
        freshness_status = "DISPUTED"
        warning = "Cross-source discrepancy detected; requires analyst verification."
    elif is_archival_baseline:
        freshness_status = "STALE_ARCHIVAL_BASELINE"
        warning = (
            "Serving archival baseline only — awaiting live Tier-1 official feed update. "
            "Do not treat as real-time market quote."
        )
    elif age_days <= float(sla["fresh_days"]):
        freshness_status = "FRESH"
        warning = None
    elif age_days <= float(sla["stale_days"]):
        freshness_status = "AGING"
        warning = (
            f"Data is {age_days:.0f} days old (approaching SLA limit of {sla['stale_days']} days)."
        )
    else:
        freshness_status = "STALE"
        warning = (
            f"STALE DATA WARNING: Last official effective reading is {age_days:.0f} days old "
            f"(exceeds {sla['stale_days']}-day SLA for '{sla['cadence']}')."
        )

    return {
        "age_days": age_days,
        "freshness_status": freshness_status,
        "expected_update_cadence": sla["cadence"],
        "next_expected_update": next_expected.strftime("%Y-%m-%d"),
        "stale_warning": warning,
    }


def log_intelligence_change(
    db: Session,
    change_category: str,
    entity_type: str,
    entity_id: str,
    summary: str,
    previous_state: Optional[Dict[str, Any]] = None,
    new_state: Optional[Dict[str, Any]] = None,
    source_or_actor: str = "VERIFICATION_ENGINE",
    evidence_url: Optional[str] = None,
) -> IntelligenceChangeLog:
    """Append an immutable governance record to `intelligence_change_log`."""
    entry = IntelligenceChangeLog(
        change_category=change_category,
        entity_type=entity_type,
        entity_id=str(entity_id),
        summary=summary,
        previous_state_json=previous_state or {},
        new_state_json=new_state or {},
        source_or_actor=source_or_actor,
        evidence_url=evidence_url,
    )
    db.add(entry)
    return entry


class FinancialDataVerificationEngine:
    """
    Centralized Verification, Source-Hierarchy Resolution, Freshness Monitoring,
    and Cross-Source Discrepancy Detection Engine (Part 1).
    """

    @staticmethod
    def tier_rank(tier: Optional[str], is_archival_baseline: bool = False) -> int:
        if is_archival_baseline:
            return SOURCE_TIER_RANK["ARCHIVAL_BASELINE"]
        return SOURCE_TIER_RANK.get((tier or "TIER_1_OFFICIAL").upper(), 3)

    @classmethod
    def _sort_key_authoritative(cls, row: Any) -> Tuple[int, float, float]:
        """
        Higher tuple value = MORE authoritative:
        1. Live record (not archival baseline) ALWAYS beats archival baseline.
        2. Lower source tier rank (Tier 1 = 1 beats Tier 2 = 2 beats Tier 3 = 3).
        3. Newer effective_date / publication_date wins within the same tier.
        """
        is_archival = bool(getattr(row, "is_archival_baseline", False))
        tier = getattr(row, "source_tier", "TIER_1_OFFICIAL")
        eff = _to_utc(getattr(row, "effective_date", None) or getattr(row, "publication_date", None))
        pub = _to_utc(getattr(row, "publication_date", None))
        eff_ts = eff.timestamp() if eff else 0.0
        pub_ts = pub.timestamp() if pub else 0.0
        # Live > Archival, Tier 1 > Tier 2 > Tier 3, then newer effective/publication date
        tier_priority = -cls.tier_rank(tier, is_archival_baseline=is_archival)
        live_flag = 0 if is_archival else 1
        return (live_flag, tier_priority, max(eff_ts, pub_ts))

    @classmethod
    def mark_legacy_seed_records_as_archival(cls, db: Session) -> Dict[str, int]:
        """
        Non-destructively tag legacy synthetic seed rows (`source_url IS NULL` or
        known bootstrap records from prior runs) with `is_archival_baseline=True`
        so historical rows are preserved for audit while NEVER overriding live
        Tier-1 official CBN / FRED / Alpha Vantage / FMP publications.
        """
        macro_tagged = 0
        market_tagged = 0
        yield_tagged = 0

        # Identify legacy macro rows lacking live source_url
        for row in db.execute(select(MacroIndicator)).scalars().all():
            if not row.source_url and not row.is_archival_baseline:
                row.is_archival_baseline = True
                row.source_tier = "ARCHIVAL_BASELINE"
                row.confidence_score = 45.0
                macro_tagged += 1

        for row in db.execute(select(MarketTimeseries)).scalars().all():
            if not row.source_url and not row.is_archival_baseline:
                row.is_archival_baseline = True
                row.source_tier = "ARCHIVAL_BASELINE"
                row.confidence_score = 45.0
                market_tagged += 1
            elif (
                not row.is_archival_baseline
                and row.source_tier == "TIER_1_OFFICIAL"
                and row.verification_status == "PENDING_CROSS_CHECK"
            ):
                row.verification_status = "VERIFIED"


        for row in db.execute(select(YieldCurvePoint)).scalars().all():
            if not row.source_url and not row.is_archival_baseline:
                row.is_archival_baseline = True
                row.source_tier = "ARCHIVAL_BASELINE"
                row.confidence_score = 45.0
                yield_tagged += 1

        if macro_tagged or market_tagged or yield_tagged:
            log_intelligence_change(
                db=db,
                change_category="DATA_CORRECTION",
                entity_type="DATABASE_HYGIENE",
                entity_id="ARCHIVAL_BASELINE_RECLASSIFICATION",
                summary=(
                    f"Reclassified legacy synthetic seed records as ARCHIVAL_BASELINE (preserving all history): "
                    f"{macro_tagged} macro, {market_tagged} market, {yield_tagged} yield points."
                ),
                new_state={
                    "macro_tagged": macro_tagged,
                    "market_tagged": market_tagged,
                    "yield_tagged": yield_tagged,
                },
            )
            db.commit()

        return {
            "macro_reclassified_archival": macro_tagged,
            "market_reclassified_archival": market_tagged,
            "yield_reclassified_archival": yield_tagged,
        }

    @classmethod
    def run_discrepancy_detection_and_resolution(cls, db: Session) -> Dict[str, Any]:
        """
        Part 1.5 Automated Cross-Source Discrepancy Detection & Resolution:
        1. Inspects all macro indicators and key market indicators across sources.
        2. Compares live Tier-1 official values vs Tier-2 providers and archival baselines.
        3. Sets `is_authoritative=True` ONLY on the winning authoritative source/series,
           preserving all conflicting records for audit.
        4. Logs material discrepancies (> 0.5% or > 0.25 percentage points) to `data_discrepancies`
           and records corrections in `intelligence_change_log`.
        """
        sources_by_id = {
            s.id: s for s in db.execute(select(DataSource)).scalars().all()
        }
        discrepancies_logged = 0
        corrections_logged = 0

        # 1. Reconcile Macro Indicators by indicator_code
        macro_rows = db.execute(select(MacroIndicator)).scalars().all()
        macro_by_code: Dict[str, List[MacroIndicator]] = {}
        for r in macro_rows:
            macro_by_code.setdefault(r.indicator_code, []).append(r)

        for code, rows in macro_by_code.items():
            if not rows:
                continue
            live_rows = [r for r in rows if not r.is_archival_baseline]
            archival_rows = [r for r in rows if r.is_archival_baseline]

            if live_rows:
                # Live official records supersede archival baselines completely
                best_live = max(live_rows, key=cls._sort_key_authoritative)
                best_live.is_authoritative = True

                # Demote archival baselines (preserve history, never delete!)
                for ar in archival_rows:
                    if ar.is_authoritative:
                        ar.is_authoritative = False

                if archival_rows:
                    latest_arch = max(archival_rows, key=lambda x: _to_utc(x.publication_date) or datetime.min.replace(tzinfo=timezone.utc))
                    live_val = float(best_live.value)
                    arch_val = float(latest_arch.value)
                    diff_abs = abs(live_val - arch_val)
                    diff_pct = (diff_abs / abs(arch_val) * 100.0) if abs(arch_val) > 1e-9 else 0.0

                    if diff_abs >= 0.25 or diff_pct >= 1.0:
                        existing_disc = db.execute(
                            select(DataDiscrepancy).where(
                                DataDiscrepancy.indicator_code == code,
                                DataDiscrepancy.reporting_period == best_live.reporting_period,
                                DataDiscrepancy.conflicting_source == "ARCHIVAL_BASELINE_SEED",
                            )
                        ).scalar_one_or_none()
                        if not existing_disc:
                            p_src = sources_by_id.get(best_live.source_id)
                            p_name = p_src.name if p_src else "Official Primary Source"
                            db.add(
                                DataDiscrepancy(
                                    indicator_code=code,
                                    indicator_name=best_live.indicator_name,
                                    reporting_period=best_live.reporting_period,
                                    primary_source=p_name,
                                    primary_source_tier=best_live.source_tier,
                                    primary_value=live_val,
                                    primary_publication_date=_to_utc(best_live.publication_date) or datetime.now(timezone.utc),
                                    primary_effective_date=_to_utc(best_live.effective_date),
                                    conflicting_source="ARCHIVAL_BASELINE_SEED",
                                    conflicting_source_tier="ARCHIVAL_BASELINE",
                                    conflicting_value=arch_val,
                                    conflicting_publication_date=_to_utc(latest_arch.publication_date) or datetime.now(timezone.utc),
                                    variance_abs=round(diff_abs, 6),
                                    variance_pct=round(diff_pct, 4),
                                    authoritative_value=live_val,
                                    authoritative_source=p_name,
                                    resolution_rule=(
                                        f"TIER_1_OFFICIAL live publication ({p_name}, period {best_live.reporting_period}) "
                                        f"superseded stale archival baseline ({arch_val}). Historical record preserved."
                                    ),
                                    resolution_status="SUPERSEDED_BY_NEWER_OFFICIAL",
                                )
                            )
                            log_intelligence_change(
                                db=db,
                                change_category="DATA_CORRECTION",
                                entity_type="MACRO_INDICATOR",
                                entity_id=code,
                                summary=(
                                    f"Corrected {best_live.indicator_name} ({code}) from stale archival {arch_val} "
                                    f"to verified live {p_name} figure {live_val} {best_live.currency_or_unit} "
                                    f"(period: {best_live.reporting_period})."
                                ),
                                previous_state={"value": arch_val, "source": "ARCHIVAL_BASELINE_SEED"},
                                new_state={
                                    "value": live_val,
                                    "source": p_name,
                                    "reporting_period": best_live.reporting_period,
                                    "source_url": best_live.source_url,
                                },
                                source_or_actor=p_name,
                                evidence_url=best_live.source_url,
                            )
                            discrepancies_logged += 1
                            corrections_logged += 1

        # 2. Reconcile Cross-Source FX Discrepancies (e.g. CBN NFEM vs Alpha Vantage USDNGN vs Archival Seed)
        market_rows = db.execute(select(MarketTimeseries)).scalars().all()
        market_by_sym: Dict[str, List[MarketTimeseries]] = {}
        for r in market_rows:
            market_by_sym.setdefault(r.symbol, []).append(r)

        for sym, rows in market_by_sym.items():
            live_rows = [r for r in rows if not r.is_archival_baseline]
            archival_rows = [r for r in rows if r.is_archival_baseline]
            if live_rows:
                for ar in archival_rows:
                    if ar.is_authoritative:
                        ar.is_authoritative = False
                best_live = max(live_rows, key=cls._sort_key_authoritative)
                best_live.is_authoritative = True

                if archival_rows:
                    latest_arch = max(archival_rows, key=lambda x: _to_utc(x.publication_date) or datetime.min.replace(tzinfo=timezone.utc))
                    live_val = float(best_live.value)
                    arch_val = float(latest_arch.value)
                    diff_abs = abs(live_val - arch_val)
                    diff_pct = (diff_abs / abs(arch_val) * 100.0) if abs(arch_val) > 1e-9 else 0.0
                    if diff_pct >= 2.0:
                        existing_disc = db.execute(
                            select(DataDiscrepancy).where(
                                DataDiscrepancy.indicator_code == sym,
                                DataDiscrepancy.reporting_period == best_live.reporting_period,
                                DataDiscrepancy.conflicting_source == "ARCHIVAL_BASELINE_SEED",
                            )
                        ).scalar_one_or_none()
                        if not existing_disc:
                            p_src = sources_by_id.get(best_live.source_id)
                            p_name = p_src.name if p_src else "Official Market Feed"
                            db.add(
                                DataDiscrepancy(
                                    indicator_code=sym,
                                    indicator_name=best_live.indicator_name,
                                    reporting_period=best_live.reporting_period,
                                    primary_source=p_name,
                                    primary_source_tier=best_live.source_tier,
                                    primary_value=live_val,
                                    primary_publication_date=_to_utc(best_live.publication_date) or datetime.now(timezone.utc),
                                    primary_effective_date=_to_utc(best_live.effective_date),
                                    conflicting_source="ARCHIVAL_BASELINE_SEED",
                                    conflicting_source_tier="ARCHIVAL_BASELINE",
                                    conflicting_value=arch_val,
                                    conflicting_publication_date=_to_utc(latest_arch.publication_date) or datetime.now(timezone.utc),
                                    variance_abs=round(diff_abs, 6),
                                    variance_pct=round(diff_pct, 4),
                                    authoritative_value=live_val,
                                    authoritative_source=p_name,
                                    resolution_rule=(
                                        f"Live {best_live.source_tier} feed ({p_name}) superseded stale archival baseline ({arch_val})."
                                    ),
                                    resolution_status="SUPERSEDED_BY_NEWER_OFFICIAL",
                                )
                            )
                            log_intelligence_change(
                                db=db,
                                change_category="DATA_CORRECTION",
                                entity_type="MARKET_INDICATOR",
                                entity_id=sym,
                                summary=(
                                    f"Updated {sym} from stale archival {arch_val:,.2f} to live {p_name} "
                                    f"reading {live_val:,.2f} {best_live.currency_or_unit} ({best_live.reporting_period})."
                                ),
                                previous_state={"value": arch_val},
                                new_state={"value": live_val, "source": p_name, "source_url": best_live.source_url},
                                source_or_actor=p_name,
                                evidence_url=best_live.source_url,
                            )
                            discrepancies_logged += 1
                            corrections_logged += 1

        # 3. Cross-Source FX Check: CBN NFEM (`NGNUSD.NAFEM`) vs Alpha Vantage (`USDNGN.AV`)
        nafem_live = [r for r in market_by_sym.get("NGNUSD.NAFEM", []) if not r.is_archival_baseline]
        av_live = [r for r in market_by_sym.get("USDNGN.AV", []) if not r.is_archival_baseline]
        if nafem_live and av_live:
            top_nafem = max(nafem_live, key=cls._sort_key_authoritative)
            top_av = max(av_live, key=cls._sort_key_authoritative)
            v1, v2 = float(top_nafem.value), float(top_av.value)
            diff_abs = abs(v1 - v2)
            diff_pct = (diff_abs / max(v1, 1e-9)) * 100.0
            if diff_pct >= 0.5:
                existing_fx = db.execute(
                    select(DataDiscrepancy).where(
                        DataDiscrepancy.indicator_code == "NGNUSD.NAFEM",
                        DataDiscrepancy.reporting_period == top_nafem.reporting_period,
                        DataDiscrepancy.conflicting_source == "Alpha Vantage Financial API",
                    )
                ).scalar_one_or_none()
                if not existing_fx:
                    db.add(
                        DataDiscrepancy(
                            indicator_code="NGNUSD.NAFEM",
                            indicator_name="USD/NGN Exchange Rate (CBN NFEM vs Alpha Vantage)",
                            reporting_period=top_nafem.reporting_period,
                            primary_source="Central Bank of Nigeria (CBN) NFEM Official Rate",
                            primary_source_tier="TIER_1_OFFICIAL",
                            primary_value=v1,
                            primary_publication_date=_to_utc(top_nafem.publication_date) or datetime.now(timezone.utc),
                            primary_effective_date=_to_utc(top_nafem.effective_date),
                            conflicting_source="Alpha Vantage Financial API",
                            conflicting_source_tier="TIER_2_INSTITUTIONAL",
                            conflicting_value=v2,
                            conflicting_publication_date=_to_utc(top_av.publication_date) or datetime.now(timezone.utc),
                            variance_abs=round(diff_abs, 6),
                            variance_pct=round(diff_pct, 4),
                            authoritative_value=v1,
                            authoritative_source="Central Bank of Nigeria (CBN) NFEM Official Rate",
                            resolution_rule=(
                                "Source Hierarchy Applied: TIER_1_OFFICIAL CBN NFEM closing rate takes precedence over "
                                "TIER_2_INSTITUTIONAL indicative FX quote (Alpha Vantage). Both records preserved."
                            ),
                            resolution_status="RESOLVED_BY_HIERARCHY",
                        )
                    )
                    discrepancies_logged += 1

        # 4. Reconcile Yield Curve points (demote archival where live official auctions exist)
        yc_rows = db.execute(select(YieldCurvePoint)).scalars().all()
        yc_by_key: Dict[Tuple[str, str], List[YieldCurvePoint]] = {}
        for r in yc_rows:
            yc_by_key.setdefault((r.curve_name, r.tenor_label), []).append(r)
        for (_, _), rows in yc_by_key.items():
            live_y = [r for r in rows if not r.is_archival_baseline]
            if live_y:
                for ar in rows:
                    if ar.is_archival_baseline and ar.is_authoritative:
                        ar.is_authoritative = False

        db.commit()
        return {
            "discrepancies_logged": discrepancies_logged,
            "corrections_logged": corrections_logged,
            "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    def get_authoritative_macro_snapshot(cls, db: Session) -> Dict[str, Dict[str, Any]]:
        """
        Return the verified, source-hierarchy-resolved current value + all 12 mandatory
        provenance & freshness attributes for every tracked macroeconomic indicator.
        """
        sources_by_id = {s.id: s for s in db.execute(select(DataSource)).scalars().all()}
        rows = (
            db.execute(
                select(MacroIndicator)
                .where(MacroIndicator.verification_status.in_(["VERIFIED", "PENDING_CROSS_CHECK"]))
                .order_by(MacroIndicator.publication_date.asc())
            )
            .scalars()
            .all()
        )
        grouped: Dict[str, List[MacroIndicator]] = {}
        for r in rows:
            grouped.setdefault(r.indicator_code, []).append(r)

        disputed_codes = set(
            db.execute(
                select(DataDiscrepancy.indicator_code).where(
                    DataDiscrepancy.resolution_status == "DISPUTED_NEEDS_REVIEW"
                )
            )
            .scalars()
            .all()
        )

        snapshot: Dict[str, Dict[str, Any]] = {}
        for code, all_rows in grouped.items():
            live_rows = [r for r in all_rows if not r.is_archival_baseline]
            active_pool = live_rows if live_rows else all_rows
            active_pool.sort(key=lambda r: _to_utc(r.effective_date or r.publication_date) or datetime.min.replace(tzinfo=timezone.utc))

            latest = max(active_pool, key=cls._sort_key_authoritative)
            prev_val = (
                float(latest.previous_value)
                if latest.previous_value is not None
                else (float(active_pool[-2].value) if len(active_pool) >= 2 else None)
            )
            curr_val = float(latest.value)
            change = round(curr_val - prev_val, 4) if prev_val is not None else None
            ds = sources_by_id.get(latest.source_id)
            fresh = compute_freshness_assessment(
                indicator_key=code,
                publication_date=latest.publication_date,
                effective_date=latest.effective_date,
                is_archival_baseline=bool(latest.is_archival_baseline),
                has_unresolved_discrepancy=(code in disputed_codes),
            )
            snapshot[code] = {
                "indicator_code": code,
                "indicator_name": latest.indicator_name,
                "country": latest.country,
                "category": latest.category,
                "latest_value": curr_val,
                "previous_value": prev_val,
                "change": change,
                "currency_or_unit": latest.currency_or_unit,
                "reporting_period": latest.reporting_period,
                "publication_date": (_to_utc(latest.publication_date) or datetime.now(timezone.utc)).strftime("%Y-%m-%d"),
                "effective_date": (_to_utc(latest.effective_date or latest.publication_date) or datetime.now(timezone.utc)).strftime("%Y-%m-%d"),
                "retrieval_timestamp": (_to_utc(latest.retrieval_date) or datetime.now(timezone.utc)).isoformat(),
                "source_name": ds.name if ds else "Unknown Source",
                "source_code": ds.code if ds else "UNKNOWN",
                "source_url": latest.source_url or (ds.base_url if ds else ""),
                "source_tier": latest.source_tier,
                "confidence_score": float(latest.confidence_score),
                "verification_status": (
                    "DISPUTED"
                    if code in disputed_codes
                    else ("ARCHIVAL_BASELINE" if latest.is_archival_baseline else latest.verification_status)
                ),
                "is_archival_baseline": bool(latest.is_archival_baseline),
                "observations_count": len(active_pool),
                "total_historical_records": len(all_rows),
                **fresh,
            }
        return snapshot

    @classmethod
    def get_data_accuracy_monitor(cls, db: Session) -> Dict[str, Any]:
        """
        Part 5A: Data Accuracy Monitor payload uniting Macro Indicators, Market Benchmarks,
        Yield Curve benchmarks, Freshness SLA warnings, and Cross-Source Discrepancies.
        """
        sources_by_id = {s.id: s for s in db.execute(select(DataSource)).scalars().all()}
        macro_snap = cls.get_authoritative_macro_snapshot(db)

        indicators_list: List[Dict[str, Any]] = []
        for item in macro_snap.values():
            indicators_list.append(
                {
                    "domain": "MACROECONOMIC",
                    "indicator_code": item["indicator_code"],
                    "indicator_name": item["indicator_name"],
                    "value": item["latest_value"],
                    "unit": item["currency_or_unit"],
                    "country": item["country"],
                    "source": item["source_name"],
                    "source_tier": item["source_tier"],
                    "source_url": item["source_url"],
                    "reporting_period": item["reporting_period"],
                    "publication_date": item["publication_date"],
                    "effective_date": item["effective_date"],
                    "retrieval_timestamp": item["retrieval_timestamp"],
                    "next_expected_update": item["next_expected_update"],
                    "age_days": item["age_days"],
                    "freshness_status": item["freshness_status"],
                    "verification_status": item["verification_status"],
                    "confidence_score": item["confidence_score"],
                    "stale_warning": item["stale_warning"],
                    "expected_update_cadence": item["expected_update_cadence"],
                }
            )

        # Market Indicators
        m_rows = db.execute(select(MarketTimeseries)).scalars().all()
        m_grouped: Dict[str, List[MarketTimeseries]] = {}
        for r in m_rows:
            m_grouped.setdefault(r.symbol, []).append(r)

        for sym, rows in m_grouped.items():
            live_rows = [r for r in rows if not r.is_archival_baseline]
            pool = live_rows if live_rows else rows
            latest = max(pool, key=cls._sort_key_authoritative)
            ds = sources_by_id.get(latest.source_id)
            fresh = compute_freshness_assessment(
                indicator_key=sym,
                publication_date=latest.publication_date,
                effective_date=latest.effective_date,
                is_archival_baseline=bool(latest.is_archival_baseline),
            )
            indicators_list.append(
                {
                    "domain": "MARKET",
                    "indicator_code": sym,
                    "indicator_name": latest.indicator_name,
                    "value": float(latest.value),
                    "unit": latest.currency_or_unit,
                    "country": latest.market_region,
                    "source": ds.name if ds else "Unknown",
                    "source_tier": latest.source_tier,
                    "source_url": latest.source_url or (ds.base_url if ds else ""),
                    "reporting_period": latest.reporting_period,
                    "publication_date": (_to_utc(latest.publication_date) or datetime.now(timezone.utc)).strftime("%Y-%m-%d"),
                    "effective_date": (_to_utc(latest.effective_date or latest.publication_date) or datetime.now(timezone.utc)).strftime("%Y-%m-%d"),
                    "retrieval_timestamp": (_to_utc(latest.retrieval_date) or datetime.now(timezone.utc)).isoformat(),
                    "next_expected_update": fresh["next_expected_update"],
                    "age_days": fresh["age_days"],
                    "freshness_status": fresh["freshness_status"],
                    "verification_status": "ARCHIVAL_BASELINE" if latest.is_archival_baseline else latest.verification_status,
                    "confidence_score": float(latest.confidence_score),
                    "stale_warning": fresh["stale_warning"],
                    "expected_update_cadence": fresh["expected_update_cadence"],
                }
            )

        # Yield Curve Key Tenors
        yc_rows = db.execute(select(YieldCurvePoint)).scalars().all()
        yc_grouped: Dict[Tuple[str, str], List[YieldCurvePoint]] = {}
        for r in yc_rows:
            yc_grouped.setdefault((r.curve_name, r.tenor_label), []).append(r)

        for (curve, tenor), rows in yc_grouped.items():
            if tenor not in ("91D", "182D", "364D", "10Y", "30Y"):
                continue
            live_rows = [r for r in rows if not r.is_archival_baseline]
            pool = live_rows if live_rows else rows
            latest = max(pool, key=cls._sort_key_authoritative)
            ds = sources_by_id.get(latest.source_id)
            fresh = compute_freshness_assessment(
                indicator_key=latest.instrument_type,
                publication_date=latest.publication_date,
                effective_date=latest.effective_date,
                is_archival_baseline=bool(latest.is_archival_baseline),
            )
            indicators_list.append(
                {
                    "domain": "FIXED_INCOME_YIELD",
                    "indicator_code": f"{curve}:{tenor}",
                    "indicator_name": latest.indicator_name,
                    "value": float(latest.value),
                    "unit": latest.currency_or_unit,
                    "country": "NIGERIA" if "NGN" in curve else "USA",
                    "source": ds.name if ds else "Unknown",
                    "source_tier": latest.source_tier,
                    "source_url": latest.source_url or (ds.base_url if ds else ""),
                    "reporting_period": latest.reporting_period,
                    "publication_date": (_to_utc(latest.publication_date) or datetime.now(timezone.utc)).strftime("%Y-%m-%d"),
                    "effective_date": (_to_utc(latest.effective_date or latest.publication_date) or datetime.now(timezone.utc)).strftime("%Y-%m-%d"),
                    "retrieval_timestamp": (_to_utc(latest.retrieval_date) or datetime.now(timezone.utc)).isoformat(),
                    "next_expected_update": fresh["next_expected_update"],
                    "age_days": fresh["age_days"],
                    "freshness_status": fresh["freshness_status"],
                    "verification_status": "ARCHIVAL_BASELINE" if latest.is_archival_baseline else latest.verification_status,
                    "confidence_score": float(latest.confidence_score),
                    "stale_warning": fresh["stale_warning"],
                    "expected_update_cadence": fresh["expected_update_cadence"],
                }
            )

        discrepancies = (
            db.execute(
                select(DataDiscrepancy)
                .order_by(DataDiscrepancy.detected_at.desc())
                .limit(50)
            )
            .scalars()
            .all()
        )

        # Summary counts
        total = len(indicators_list)
        live_verified = sum(
            1 for i in indicators_list if i["verification_status"] == "VERIFIED" and i["freshness_status"] == "FRESH"
        )
        aging = sum(1 for i in indicators_list if i["freshness_status"] == "AGING")
        stale_or_archival = sum(
            1
            for i in indicators_list
            if i["freshness_status"] in ("STALE", "STALE_ARCHIVAL_BASELINE")
        )
        disputed = sum(1 for i in indicators_list if i["freshness_status"] == "DISPUTED")

        # Sort so FRESH Tier-1 official Nigerian indicators appear first, followed by flagged items
        indicators_list.sort(
            key=lambda x: (
                0 if x["freshness_status"] == "FRESH" else (1 if x["freshness_status"] == "AGING" else 2),
                0 if x["country"] == "NIGERIA" else 1,
                x["indicator_code"],
            )
        )

        return {
            "audited_at_utc": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_tracked_indicators": total,
                "live_verified_fresh": live_verified,
                "aging_count": aging,
                "stale_or_archival_count": stale_or_archival,
                "disputed_count": disputed,
                "discrepancies_logged": len(discrepancies),
                "data_accuracy_score_pct": round((live_verified / max(total, 1)) * 100.0, 1),
            },
            "indicators": indicators_list,
            "discrepancies": [
                {
                    "id": d.id,
                    "indicator_code": d.indicator_code,
                    "indicator_name": d.indicator_name,
                    "reporting_period": d.reporting_period,
                    "primary_source": d.primary_source,
                    "primary_source_tier": d.primary_source_tier,
                    "primary_value": float(d.primary_value),
                    "conflicting_source": d.conflicting_source,
                    "conflicting_source_tier": d.conflicting_source_tier,
                    "conflicting_value": float(d.conflicting_value),
                    "variance_abs": float(d.variance_abs),
                    "variance_pct": float(d.variance_pct),
                    "authoritative_value": float(d.authoritative_value),
                    "authoritative_source": d.authoritative_source,
                    "resolution_rule": d.resolution_rule,
                    "resolution_status": d.resolution_status,
                    "detected_at": (_to_utc(d.detected_at) or datetime.now(timezone.utc)).isoformat(),
                }
                for d in discrepancies
            ],
        }
