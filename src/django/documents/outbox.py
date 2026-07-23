from collections.abc import Mapping
from datetime import datetime, timedelta
from types import MappingProxyType
from uuid import UUID, uuid4

from django.db import transaction
from django.db.models import F, Q

from .contracts import (
    ClaimedDocumentEvent,
    DocumentEventEnvelope,
    FailureDisposition,
    safe_error_code,
)
from .models import DocumentOutboxEvent

DATABASE_ALIAS = "documents"


def append_document_event(
    *,
    event_type: str,
    document_id: UUID,
    content_revision: int,
    source_sha256: str,
    payload: Mapping[str, object],
) -> DocumentOutboxEvent:
    return DocumentOutboxEvent.objects.using(DATABASE_ALIAS).create(
        event_type=event_type,
        document_id=document_id,
        content_revision=content_revision,
        source_sha256=source_sha256,
        payload=dict(payload),
    )


def _envelope(event: DocumentOutboxEvent) -> DocumentEventEnvelope:
    return DocumentEventEnvelope(
        event_id=event.id,
        event_type=event.event_type,
        schema_version=event.schema_version,
        document_id=event.document_id,
        content_revision=event.content_revision,
        source_sha256=event.source_sha256,
        payload=MappingProxyType(dict(event.payload)),
        occurred_at=event.occurred_at,
    )


def _eligible(now: datetime) -> Q:
    return Q(
        status=DocumentOutboxEvent.Status.PENDING,
        available_at__lte=now,
    ) | Q(
        status=DocumentOutboxEvent.Status.CLAIMED,
        claim_expires_at__lte=now,
    )


def claim_events(
    *,
    now: datetime,
    batch_size: int,
    lease_seconds: int,
) -> list[ClaimedDocumentEvent]:
    if batch_size < 1 or lease_seconds < 1:
        raise ValueError("batch_size and lease_seconds must be positive")

    claimed: list[ClaimedDocumentEvent] = []
    with transaction.atomic(using=DATABASE_ALIAS):
        candidate_ids = list(
            DocumentOutboxEvent.objects.using(DATABASE_ALIAS)
            .filter(_eligible(now))
            .order_by("available_at", "occurred_at", "id")
            .values_list("id", flat=True)[:batch_size]
        )
        for event_id in candidate_ids:
            claim_token = uuid4()
            updated = (
                DocumentOutboxEvent.objects.using(DATABASE_ALIAS)
                .filter(pk=event_id)
                .filter(_eligible(now))
                .update(
                    status=DocumentOutboxEvent.Status.CLAIMED,
                    claim_token=claim_token,
                    claim_expires_at=now + timedelta(seconds=lease_seconds),
                    attempt_count=F("attempt_count") + 1,
                    last_error_code="",
                )
            )
            if not updated:
                continue
            event = DocumentOutboxEvent.objects.using(DATABASE_ALIAS).get(pk=event_id)
            claimed.append(
                ClaimedDocumentEvent(
                    envelope=_envelope(event),
                    claim_token=claim_token,
                    attempt_count=event.attempt_count,
                )
            )
    return claimed


def mark_dispatched(
    event_id,
    claim_token,
    *,
    now: datetime,
) -> bool:
    updated = (
        DocumentOutboxEvent.objects.using(DATABASE_ALIAS)
        .filter(
            pk=event_id,
            status=DocumentOutboxEvent.Status.CLAIMED,
            claim_token=claim_token,
        )
        .update(
            status=DocumentOutboxEvent.Status.DISPATCHED,
            dispatched_at=now,
            claim_token=None,
            claim_expires_at=None,
            last_error_code="",
        )
    )
    return bool(updated)


def mark_failed(
    event_id,
    claim_token,
    *,
    error_code: str,
    now: datetime,
    max_attempts: int,
) -> FailureDisposition | None:
    safe_code = safe_error_code(error_code)
    with transaction.atomic(using=DATABASE_ALIAS):
        event = (
            DocumentOutboxEvent.objects.using(DATABASE_ALIAS)
            .filter(
                pk=event_id,
                status=DocumentOutboxEvent.Status.CLAIMED,
                claim_token=claim_token,
            )
            .first()
        )
        if event is None:
            return None
        common = {
            "claim_token": None,
            "claim_expires_at": None,
            "last_error_code": safe_code,
        }
        if event.attempt_count >= max_attempts:
            DocumentOutboxEvent.objects.using(DATABASE_ALIAS).filter(pk=event.id).update(
                status=DocumentOutboxEvent.Status.DEAD_LETTER,
                **common,
            )
            return FailureDisposition.DEAD_LETTERED

        delay_seconds = min(5 * (2 ** (event.attempt_count - 1)), 15 * 60)
        DocumentOutboxEvent.objects.using(DATABASE_ALIAS).filter(pk=event.id).update(
            status=DocumentOutboxEvent.Status.PENDING,
            available_at=now + timedelta(seconds=delay_seconds),
            **common,
        )
        return FailureDisposition.RETRIED


def requeue_dead_letter(event_id, *, now: datetime) -> bool:
    updated = (
        DocumentOutboxEvent.objects.using(DATABASE_ALIAS)
        .filter(pk=event_id, status=DocumentOutboxEvent.Status.DEAD_LETTER)
        .update(
            status=DocumentOutboxEvent.Status.PENDING,
            available_at=now,
            claim_token=None,
            claim_expires_at=None,
            attempt_count=0,
            last_error_code="",
            dispatched_at=None,
        )
    )
    return bool(updated)


def count_eligible_events(*, now: datetime) -> int:
    return (
        DocumentOutboxEvent.objects.using(DATABASE_ALIAS)
        .filter(_eligible(now))
        .count()
    )
