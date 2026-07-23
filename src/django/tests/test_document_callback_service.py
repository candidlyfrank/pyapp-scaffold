from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from document_integrations.callback_service import DirectCallbackService
from document_integrations.ports import CallbackDeliveryError
from documents.contracts import (
    ClaimedDocumentEvent,
    DocumentEventEnvelope,
    FailureDisposition,
)

NOW = datetime(2026, 7, 23, 12, tzinfo=UTC)


def claimed_event():
    return ClaimedDocumentEvent(
        envelope=DocumentEventEnvelope(
            event_id=uuid4(),
            event_type="document.created",
            schema_version=1,
            document_id=uuid4(),
            content_revision=1,
            source_sha256="a" * 64,
            payload={"filename": "notes.txt"},
            occurred_at=NOW,
        ),
        claim_token=uuid4(),
        attempt_count=1,
    )


class FakeClock:
    def now(self):
        return NOW


class FakeOutbox:
    def __init__(self, events):
        self.events = events
        self.dispatched = []
        self.failed = []

    def claim(self, *, now, batch_size, lease_seconds):
        return self.events

    def mark_dispatched(self, event_id, claim_token, *, now):
        self.dispatched.append(event_id)
        return True

    def mark_failed(self, event_id, claim_token, *, error_code, now, max_attempts):
        self.failed.append((event_id, error_code))
        return FailureDisposition.RETRIED

    def count_eligible(self, *, now):
        return len(self.events)

    def requeue_dead_letter(self, event_id, *, now):
        return True


class FakeCallback:
    def __init__(self, failures=None):
        self.failures = failures or {}
        self.handled = []

    def handle(self, event):
        self.handled.append(event.event_id)
        failure = self.failures.get(event.event_id)
        if failure:
            raise failure


def test_dispatches_success_and_continues_after_failure():
    failed = claimed_event()
    successful = claimed_event()
    outbox = FakeOutbox([failed, successful])
    callback = FakeCallback(
        {
            failed.envelope.event_id: CallbackDeliveryError(
                "callback_unavailable",
            )
        }
    )
    service = DirectCallbackService(
        outbox=outbox,
        callback=callback,
        clock=FakeClock(),
        batch_size=50,
        lease_seconds=60,
        max_attempts=8,
    )

    report = service.dispatch_once()

    assert report.claimed == 2
    assert report.dispatched == 1
    assert report.retried == 1
    assert report.dead_lettered == 0
    assert outbox.dispatched == [successful.envelope.event_id]


def test_unexpected_callback_error_uses_safe_code():
    event = claimed_event()
    outbox = FakeOutbox([event])
    callback = FakeCallback({event.envelope.event_id: RuntimeError("secret")})
    service = DirectCallbackService(
        outbox=outbox,
        callback=callback,
        clock=FakeClock(),
        batch_size=1,
        lease_seconds=60,
        max_attempts=8,
    )

    service.dispatch_once()

    assert outbox.failed == [(event.envelope.event_id, "callback_failed")]


def test_callback_error_rejects_non_machine_readable_code():
    assert CallbackDeliveryError("/private/secret").code == "callback_failed"


def test_unsupported_event_schema_is_retried_without_invoking_callback():
    item = claimed_event()
    unsupported = replace(
        item,
        envelope=replace(item.envelope, schema_version=2),
    )
    outbox = FakeOutbox([unsupported])
    callback = FakeCallback()
    service = DirectCallbackService(
        outbox=outbox,
        callback=callback,
        clock=FakeClock(),
        batch_size=1,
        lease_seconds=60,
        max_attempts=8,
    )

    service.dispatch_once()

    assert callback.handled == []
    assert outbox.failed == [
        (unsupported.envelope.event_id, "unsupported_event_schema")
    ]
