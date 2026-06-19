"""SQLAlchemy ORM models.

Imported for side effects so ``Base.metadata`` is fully populated.
"""
from app.models.discovery_run import DiscoveryRun, SourceDocument
from app.models.raw_signal import RawSignal
from app.models.normalized_signal import NormalizedSignal
from app.models.opportunity import Opportunity, OpportunitySignal
from app.models.retailer import Retailer
from app.models.retailer_scan import RetailerScan
from app.models.scan_item import ScanItem
from app.models.coverage_snapshot import CoverageSnapshot
from app.models.transferability import TransferabilityAssessment
from app.models.recommendation import Recommendation

__all__ = [
    "DiscoveryRun",
    "SourceDocument",
    "RawSignal",
    "NormalizedSignal",
    "Opportunity",
    "OpportunitySignal",
    "Retailer",
    "RetailerScan",
    "ScanItem",
    "CoverageSnapshot",
    "TransferabilityAssessment",
    "Recommendation",
]
