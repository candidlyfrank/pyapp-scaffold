from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.db.models.query import QuerySet

from documents.contracts import FailureDisposition
from documents.models import DocumentOutboxEvent
from documents.outbox import (
    claim_events,
    count_eligible_events,
    mark_dispatched,
    mark_failed,
    requeue_dead_letter,
)


def make_event(*, available_at=None, status=DocumentOutboxEvent.Status.PENDING):
    event = DocumentOutboxEvent.objects.create(
        event_type=DocumentOutboxEvent.EventType.CREATED,
        document_id=uuid4(),
        content_revision=1,
        source_sha256="a" * 64,
        payload={"filename": "notes.txt"},
        status=status,
    )
    if available_at is not None:
        DocumentOutboxEvent.objects.filter(pk=event.pk).update(available_at=available_at)
        event.refresh_from_db()
    return event


@pytest.mark.django_db(databases=["documents"])
def test_claims_due_events_without_claiming_future_events():
    now = datetime(2026, 7, 23, 12, tzinfo=UTC)
    due = make_event(available_at=now)
    future = make_event(available_at=now + timedelta(minutes=1))

    claimed = claim_events(now=now, batch_size=10, lease_seconds=60)

    assert [item.envelope.event_id for item in claimed] == [due.id]
    due.refresh_from_db()
    future.refresh_from_db()
    assert due.status == DocumentOutboxEvent.Status.CLAIMED
    assert due.attempt_count == 1
    assert future.status == DocumentOutboxEvent.Status.PENDING


@pytest.mark.django_db(databases=["documents"])
def test_reclaims_expired_lease_with_new_token():
    now = datetime(2026, 7, 23, 12, tzinfo=UTC)
    event = make_event(status=DocumentOutboxEvent.Status.CLAIMED)
    old_token = uuid4()
    DocumentOutboxEvent.objects.filter(pk=event.pk).update(
        claim_token=old_token,
        claim_expires_at=now - timedelta(seconds=1),
    )

    claimed = claim_events(now=now, batch_size=1, lease_seconds=60)

    assert claimed[0].claim_token != old_token
    assert claimed[0].attempt_count == 1


@pytest.mark.django_db(databases=["documents"])
def test_does_not_steal_active_lease():
    now = datetime(2026, 7, 23, 12, tzinfo=UTC)
    event = make_event(status=DocumentOutboxEvent.Status.CLAIMED)
    DocumentOutboxEvent.objects.filter(pk=event.pk).update(
        claim_token=uuid4(),
        claim_expires_at=now + timedelta(seconds=1),
    )

    assert claim_events(now=now, batch_size=1, lease_seconds=60) == []


@pytest.mark.django_db(databases=["documents"])
def test_stale_token_cannot_mark_event_dispatched():
    now = datetime(2026, 7, 23, 12, tzinfo=UTC)
    event = make_event(available_at=now)
    claimed = claim_events(now=now, batch_size=1, lease_seconds=60)[0]

    assert mark_dispatched(event.id, uuid4(), now=now) is False
    assert mark_dispatched(event.id, claimed.claim_token, now=now) is True


@pytest.mark.django_db(databases=["documents"])
def test_failure_retries_with_bounded_backoff_then_dead_letters():
    now = datetime(2026, 7, 23, 12, tzinfo=UTC)
    event = make_event(available_at=now)
    DocumentOutboxEvent.objects.filter(pk=event.pk).update(attempt_count=6)
    claim = claim_events(now=now, batch_size=1, lease_seconds=60)[0]

    retry = mark_failed(
        event.id,
        claim.claim_token,
        error_code="callback_unavailable",
        now=now,
        max_attempts=8,
    )
    event.refresh_from_db()
    assert retry == FailureDisposition.RETRIED
    assert event.available_at == now + timedelta(seconds=320)

    next_claim = claim_events(
        now=event.available_at,
        batch_size=1,
        lease_seconds=60,
    )[0]
    dead = mark_failed(
        event.id,
        next_claim.claim_token,
        error_code="callback_unavailable",
        now=event.available_at,
        max_attempts=8,
    )
    event.refresh_from_db()
    assert dead == FailureDisposition.DEAD_LETTERED
    assert event.status == DocumentOutboxEvent.Status.DEAD_LETTER


@pytest.mark.django_db(databases=["documents"])
def test_dead_letter_can_be_requeued_and_due_events_counted():
    now = datetime(2026, 7, 23, 12, tzinfo=UTC)
    event = make_event(status=DocumentOutboxEvent.Status.DEAD_LETTER)

    assert requeue_dead_letter(event.id, now=now) is True
    assert count_eligible_events(now=now) == 1


@pytest.mark.django_db(databases=["documents"])
def test_stale_token_cannot_mark_event_failed():
    now = datetime(2026, 7, 23, 12, tzinfo=UTC)
    event = make_event(available_at=now)
    claimed = claim_events(now=now, batch_size=1, lease_seconds=60)[0]

    assert (
        mark_failed(
            event.id,
            uuid4(),
            error_code="callback_unavailable",
            now=now,
            max_attempts=8,
        )
        is None
    )
    event.refresh_from_db()
    assert event.status == DocumentOutboxEvent.Status.CLAIMED
    assert event.claim_token == claimed.claim_token


@pytest.mark.django_db(databases=["documents"])
def test_lost_failure_transition_race_preserves_new_claim():
    now = datetime(2026, 7, 23, 12, tzinfo=UTC)
    event = make_event(available_at=now)
    claimed = claim_events(now=now, batch_size=1, lease_seconds=60)[0]
    new_token = uuid4()
    original_update = QuerySet.update

    def change_claim_before_final_update(queryset, **kwargs):
        original_update(
            DocumentOutboxEvent.objects.filter(pk=event.id),
            claim_token=new_token,
        )
        return original_update(queryset, **kwargs)

    with patch.object(
        QuerySet,
        "update",
        autospec=True,
        side_effect=change_claim_before_final_update,
    ):
        result = mark_failed(
            event.id,
            claimed.claim_token,
            error_code="callback_unavailable",
            now=now,
            max_attempts=8,
        )

    event.refresh_from_db()
    assert result is None
    assert event.status == DocumentOutboxEvent.Status.CLAIMED
    assert event.claim_token == new_token
