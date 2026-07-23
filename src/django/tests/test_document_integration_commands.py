from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import CommandError, call_command

from document_integrations.contracts import DispatchReport
from documents.models import Document


class SuccessfulCallback:
    def handle(self, event):
        return None


@pytest.mark.django_db(databases=["documents"])
def test_dispatch_dry_run_does_not_require_callback(settings):
    settings.DOCUMENT_EVENT_CALLBACK = ""
    output = StringIO()

    call_command("dispatch_document_outbox", "--dry-run", stdout=output)

    assert "eligible=0" in output.getvalue()


def test_dispatch_requires_callback_for_delivery(settings):
    settings.DOCUMENT_EVENT_CALLBACK = ""

    with pytest.raises(CommandError, match="DOCUMENT_EVENT_CALLBACK"):
        call_command("dispatch_document_outbox")


def test_dispatch_options_override_settings_defaults(settings):
    settings.DOCUMENT_EVENT_CALLBACK = f"{__name__}.SuccessfulCallback"
    with patch(
        "document_integrations.management.commands.dispatch_document_outbox."
        "DirectCallbackService"
    ) as service_class:
        service_class.return_value.dispatch_once.return_value = DispatchReport(
            claimed=0,
            dispatched=0,
            retried=0,
            dead_lettered=0,
        )
        call_command(
            "dispatch_document_outbox",
            "--batch-size",
            "7",
            "--lease-seconds",
            "30",
            "--max-attempts",
            "4",
        )

    assert service_class.call_args.kwargs["batch_size"] == 7
    assert service_class.call_args.kwargs["lease_seconds"] == 30
    assert service_class.call_args.kwargs["max_attempts"] == 4


def test_reconcile_requires_state_adapter(settings):
    settings.DOCUMENT_RAG_REVISION_STATE_READER = ""

    with pytest.raises(
        CommandError,
        match="DOCUMENT_RAG_REVISION_STATE_READER",
    ):
        call_command("reconcile_document_revisions", "--dry-run")


@pytest.mark.django_db(databases=["documents"])
def test_reconcile_dry_run_does_not_require_command_sink(settings):
    settings.DOCUMENT_RAG_REVISION_STATE_READER = f"{__name__}.EmptyState"
    settings.DOCUMENT_RAG_SYNC_COMMAND_SINK = ""
    output = StringIO()

    call_command("reconcile_document_revisions", "--dry-run", stdout=output)

    assert "requested_sync=0" in output.getvalue()


class EmptyState:
    def list_indexed(self):
        return []


class FailingSink:
    def request_sync(self, snapshot):
        raise RuntimeError("unavailable")

    def request_delete(self, document_id):
        raise RuntimeError("unavailable")


@pytest.mark.django_db(databases=["documents"])
def test_reconcile_can_fail_command_when_an_item_fails(settings):
    Document.objects.create(
        file="storage-name",
        filename="notes.txt",
        title="notes",
        content_type="text/plain",
        size=5,
        sha256="a" * 64,
    )
    settings.DOCUMENT_RAG_REVISION_STATE_READER = f"{__name__}.EmptyState"
    settings.DOCUMENT_RAG_SYNC_COMMAND_SINK = f"{__name__}.FailingSink"

    with pytest.raises(CommandError, match="failed for 1 item"):
        call_command(
            "reconcile_document_revisions",
            "--fail-on-item-error",
        )
