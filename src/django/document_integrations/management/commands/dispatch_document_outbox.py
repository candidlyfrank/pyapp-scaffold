from uuid import UUID

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError

from document_integrations.adapters.django_documents import (
    DjangoOutboxAdapter,
    SystemClock,
)
from document_integrations.adapters.import_string import load_configured_adapter
from document_integrations.callback_service import DirectCallbackService


class Command(BaseCommand):
    help = "Dispatch one bounded batch of document outbox events."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=settings.DOCUMENT_OUTBOX_BATCH_SIZE,
        )
        parser.add_argument(
            "--lease-seconds",
            type=int,
            default=settings.DOCUMENT_OUTBOX_LEASE_SECONDS,
        )
        parser.add_argument(
            "--max-attempts",
            type=int,
            default=settings.DOCUMENT_OUTBOX_MAX_ATTEMPTS,
        )
        parser.add_argument("--requeue-dead-letter", type=UUID)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        outbox = DjangoOutboxAdapter()
        clock = SystemClock()
        event_id = options["requeue_dead_letter"]
        if event_id is not None:
            if not outbox.requeue_dead_letter(event_id, now=clock.now()):
                raise CommandError("The requested dead-letter event was not found.")
            self.stdout.write(f"requeued={event_id}")
            return

        if options["dry_run"]:
            self.stdout.write(f"eligible={outbox.count_eligible(now=clock.now())}")
            return

        try:
            callback = load_configured_adapter(
                "DOCUMENT_EVENT_CALLBACK",
                required_methods=("handle",),
            )
        except ImproperlyConfigured as error:
            raise CommandError(str(error)) from error

        service = DirectCallbackService(
            outbox=outbox,
            callback=callback,
            clock=clock,
            batch_size=options["batch_size"],
            lease_seconds=options["lease_seconds"],
            max_attempts=options["max_attempts"],
        )
        report = service.dispatch_once()
        self.stdout.write(
            " ".join(
                [
                    f"claimed={report.claimed}",
                    f"dispatched={report.dispatched}",
                    f"retried={report.retried}",
                    f"dead_lettered={report.dead_lettered}",
                ]
            )
        )
