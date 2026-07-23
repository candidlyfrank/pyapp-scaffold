from django.utils import timezone

from documents.outbox import (
    claim_events,
    count_eligible_events,
    mark_dispatched,
    mark_failed,
    requeue_dead_letter,
)
from documents.revisions import list_document_revisions


class SystemClock:
    def now(self):
        return timezone.now()


class DjangoOutboxAdapter:
    def claim(self, *, now, batch_size, lease_seconds):
        return claim_events(
            now=now,
            batch_size=batch_size,
            lease_seconds=lease_seconds,
        )

    def mark_dispatched(self, event_id, claim_token, *, now):
        return mark_dispatched(event_id, claim_token, now=now)

    def mark_failed(
        self,
        event_id,
        claim_token,
        *,
        error_code,
        now,
        max_attempts,
    ):
        return mark_failed(
            event_id,
            claim_token,
            error_code=error_code,
            now=now,
            max_attempts=max_attempts,
        )

    def count_eligible(self, *, now):
        return count_eligible_events(now=now)

    def requeue_dead_letter(self, event_id, *, now):
        return requeue_dead_letter(event_id, now=now)


class DjangoDocumentRevisionRepository:
    def list_current(self):
        return list_document_revisions()
