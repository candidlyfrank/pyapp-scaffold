from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError

from document_integrations.adapters.django_documents import (
    DjangoDocumentRevisionRepository,
)
from document_integrations.adapters.import_string import load_configured_adapter
from document_integrations.polling_service import RevisionPollingService


class DryRunSink:
    def request_sync(self, snapshot):
        return None

    def request_delete(self, document_id):
        return None


class Command(BaseCommand):
    help = "Reconcile current document revisions with configured RAG state."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--fail-on-item-error", action="store_true")

    def handle(self, *args, **options):
        try:
            state = load_configured_adapter(
                "DOCUMENT_RAG_REVISION_STATE_READER",
                required_methods=("list_indexed",),
            )
            commands = (
                DryRunSink()
                if options["dry_run"]
                else load_configured_adapter(
                    "DOCUMENT_RAG_SYNC_COMMAND_SINK",
                    required_methods=("request_sync", "request_delete"),
                )
            )
        except ImproperlyConfigured as error:
            raise CommandError(str(error)) from error

        service = RevisionPollingService(
            documents=DjangoDocumentRevisionRepository(),
            rag_state=state,
            commands=commands,
        )
        report = service.reconcile(dry_run=options["dry_run"])
        self.stdout.write(
            " ".join(
                [
                    f"source_count={report.source_count}",
                    f"indexed_count={report.indexed_count}",
                    f"requested_sync={report.requested_sync}",
                    f"requested_delete={report.requested_delete}",
                    f"current={report.current}",
                    f"failed={report.failed}",
                ]
            )
        )
        if options["fail_on_item_error"] and report.failed:
            raise CommandError(f"Reconciliation failed for {report.failed} item(s).")
