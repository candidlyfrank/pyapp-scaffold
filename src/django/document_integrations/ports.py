from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from documents.contracts import (
    ClaimedDocumentEvent,
    DocumentEventEnvelope,
    DocumentRevisionSnapshot,
    FailureDisposition,
    safe_error_code,
)

from .contracts import IndexedDocumentRevision


class CallbackDeliveryError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = safe_error_code(code)


class Clock(Protocol):
    def now(self) -> datetime:
        pass


class DocumentEventCallback(Protocol):
    def handle(self, event: DocumentEventEnvelope) -> None:
        pass


class OutboxPort(Protocol):
    def claim(
        self,
        *,
        now: datetime,
        batch_size: int,
        lease_seconds: int,
    ) -> Sequence[ClaimedDocumentEvent]:
        pass

    def mark_dispatched(self, event_id: UUID, claim_token: UUID, *, now: datetime) -> bool:
        pass

    def mark_failed(
        self,
        event_id: UUID,
        claim_token: UUID,
        *,
        error_code: str,
        now: datetime,
        max_attempts: int,
    ) -> FailureDisposition | None:
        pass

    def count_eligible(self, *, now: datetime) -> int:
        pass

    def requeue_dead_letter(self, event_id: UUID, *, now: datetime) -> bool:
        pass


class DocumentRevisionRepository(Protocol):
    def list_current(self) -> Sequence[DocumentRevisionSnapshot]:
        pass


class RagRevisionStateReader(Protocol):
    def list_indexed(self) -> Sequence[IndexedDocumentRevision]:
        pass


class RagSyncCommandSink(Protocol):
    def request_sync(self, snapshot: DocumentRevisionSnapshot) -> None:
        pass

    def request_delete(self, document_id: UUID) -> None:
        pass
