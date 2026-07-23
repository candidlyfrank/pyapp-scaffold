from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class DispatchReport:
    claimed: int
    dispatched: int
    retried: int
    dead_lettered: int


@dataclass(frozen=True)
class IndexedDocumentRevision:
    document_id: UUID
    content_revision: int
    source_sha256: str
    source_updated_at: datetime


@dataclass(frozen=True)
class ReconciliationReport:
    source_count: int
    indexed_count: int
    requested_sync: int
    requested_delete: int
    current: int
    failed: int
