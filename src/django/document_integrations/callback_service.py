import logging

from documents.contracts import FailureDisposition

from .contracts import DispatchReport
from .ports import CallbackDeliveryError, Clock, DocumentEventCallback, OutboxPort

logger = logging.getLogger(__name__)


class DirectCallbackService:
    def __init__(
        self,
        *,
        outbox: OutboxPort,
        callback: DocumentEventCallback,
        clock: Clock,
        batch_size: int,
        lease_seconds: int,
        max_attempts: int,
    ):
        if min(batch_size, lease_seconds, max_attempts) < 1:
            raise ValueError("callback service limits must be positive")
        self.outbox = outbox
        self.callback = callback
        self.clock = clock
        self.batch_size = batch_size
        self.lease_seconds = lease_seconds
        self.max_attempts = max_attempts

    def eligible_count(self) -> int:
        return self.outbox.count_eligible(now=self.clock.now())

    def dispatch_once(self) -> DispatchReport:
        now = self.clock.now()
        claimed = self.outbox.claim(
            now=now,
            batch_size=self.batch_size,
            lease_seconds=self.lease_seconds,
        )
        dispatched = 0
        retried = 0
        dead_lettered = 0

        for item in claimed:
            if item.envelope.schema_version != 1:
                code = "unsupported_event_schema"
            else:
                try:
                    self.callback.handle(item.envelope)
                except CallbackDeliveryError as error:
                    code = error.code
                except Exception:
                    logger.error(
                        "Unexpected callback failure for event %s.",
                        item.envelope.event_id,
                    )
                    code = "callback_failed"
                else:
                    if self.outbox.mark_dispatched(
                        item.envelope.event_id,
                        item.claim_token,
                        now=self.clock.now(),
                    ):
                        dispatched += 1
                    continue

            disposition = self.outbox.mark_failed(
                item.envelope.event_id,
                item.claim_token,
                error_code=code,
                now=self.clock.now(),
                max_attempts=self.max_attempts,
            )
            if disposition == FailureDisposition.RETRIED:
                retried += 1
            elif disposition == FailureDisposition.DEAD_LETTERED:
                dead_lettered += 1

        return DispatchReport(
            claimed=len(claimed),
            dispatched=dispatched,
            retried=retried,
            dead_lettered=dead_lettered,
        )
