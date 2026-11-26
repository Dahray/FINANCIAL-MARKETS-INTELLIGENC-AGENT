"""Export all 28 SQLAlchemy 2.0 ORM models for metadata registration and Alembic migrations."""

from app.models.document import DocumentChunk, ResearchDocument
from app.models.forecast import ForecastBacktest, QuantForecast
from app.models.intelligence import (
    CompetitorEvent,
    CompetitorProfile,
    MarketDevelopment,
    RegulatoryEvent,
)
from app.models.macro import MacroIndicator
from app.models.market import MarketTimeseries, YieldCurvePoint
from app.models.memory import (
    DataDiscrepancy,
    ForecastOutcome,
    IdentifiedRisk,
    IntelligenceChangeLog,
    KnowledgeGraphEdge,
    KnowledgeGraphNode,
    OpportunityEvaluation,
    ResearchFinding,
    ResearchPerformanceEvaluation,
    StrategicRecommendation,
)
from app.models.opportunity import Opportunity
from app.models.report import AgentRun, EditorialReview, WeeklyReport
from app.models.source import DataSource, SourceRegister
from app.models.user import AlertPreference, AuditLog, User

__all__ = [
    "User",
    "AuditLog",
    "AlertPreference",
    "DataSource",
    "SourceRegister",
    "MarketTimeseries",
    "YieldCurvePoint",
    "MacroIndicator",
    "ResearchDocument",
    "DocumentChunk",
    "MarketDevelopment",
    "CompetitorProfile",
    "CompetitorEvent",
    "RegulatoryEvent",
    "Opportunity",
    "QuantForecast",
    "ForecastBacktest",
    "AgentRun",
    "EditorialReview",
    "WeeklyReport",
    # Stage 2-4 Institutional Verification, Research Memory & Knowledge Graph Models
    "DataDiscrepancy",
    "IntelligenceChangeLog",
    "ResearchFinding",
    "StrategicRecommendation",
    "IdentifiedRisk",
    "ForecastOutcome",
    "ResearchPerformanceEvaluation",
    "OpportunityEvaluation",
    "KnowledgeGraphNode",
    "KnowledgeGraphEdge",
]
