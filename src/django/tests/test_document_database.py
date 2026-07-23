import json
import subprocess
import sys
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from django.conf import settings

from documents.contracts import DocumentEventEnvelope
from documents.models import Document, DocumentOutboxEvent
from documents.router import DocumentDatabaseRouter


def test_documents_database_is_separate_sqlite():
    script = """
import json
from app import settings
database = settings.DATABASES["documents"]
print(json.dumps({
    "engine": database["ENGINE"],
    "name": str(database["NAME"]),
    "dependencies": database["TEST"]["DEPENDENCIES"],
}))
"""
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )
    database = json.loads(result.stdout)

    assert database["engine"] == "django.db.backends.sqlite3"
    assert Path(database["name"]).name == "metadata.sqlite3"
    assert database["dependencies"] == []
    assert settings.DOCUMENT_DATA_ROOT.is_dir()
    assert settings.DOCUMENT_MAX_UPLOAD_BYTES == 25 * 1024 * 1024


def test_router_isolates_document_models():
    router = DocumentDatabaseRouter()

    assert router.db_for_read(Document) == "documents"
    assert router.db_for_write(Document) == "documents"
    assert router.allow_migrate("documents", "documents", model_name="document") is True
    assert router.allow_migrate("default", "documents", model_name="document") is False
    assert router.allow_migrate("documents", "auth", model_name="user") is False


@pytest.mark.django_db(databases=["documents"])
def test_document_defaults_are_stored_in_sqlite():
    document = Document.objects.create(
        file="a1b2c3",
        filename="report.txt",
        title="report",
        content_type="text/plain",
        size=6,
        sha256="0" * 64,
    )

    loaded = Document.objects.get(pk=document.pk)
    assert loaded.description == ""
    assert loaded.tags == []
    assert loaded._state.db == "documents"


def test_event_envelope_is_immutable_and_path_free():
    event = DocumentEventEnvelope(
        event_id=uuid4(),
        event_type="document.created",
        schema_version=1,
        document_id=uuid4(),
        content_revision=1,
        source_sha256="a" * 64,
        payload={"filename": "notes.txt"},
        occurred_at=datetime.now(timezone.utc),
    )

    with pytest.raises(FrozenInstanceError):
        event.content_revision = 2

    with pytest.raises(TypeError):
        event.payload["filename"] = "changed.txt"

    assert "file" not in event.__dict__
    assert "path" not in event.__dict__


@pytest.mark.django_db(databases=["documents"])
def test_document_revision_and_outbox_are_stored_in_documents_database():
    document = Document.objects.create(
        file="a1b2c3",
        filename="report.txt",
        title="report",
        content_type="text/plain",
        size=6,
        sha256="0" * 64,
    )
    event = DocumentOutboxEvent.objects.create(
        event_type=DocumentOutboxEvent.EventType.CREATED,
        document_id=document.id,
        content_revision=document.content_revision,
        source_sha256=document.sha256,
        payload={"filename": document.filename},
    )

    assert document.content_revision == 1
    assert event.status == DocumentOutboxEvent.Status.PENDING
    assert event.attempt_count == 0
    assert event._state.db == "documents"
