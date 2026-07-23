# Document RAG Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a transactional document outbox, a working direct-callback dispatcher, and a working scheduled revision-reconciliation service while keeping the document app independent from every future RAG implementation.

**Architecture:** The `documents` app remains the source-of-truth producer and owns content revisions, immutable event contracts, outbox persistence, and revision snapshots in its dedicated SQLite database. A model-free `document_integrations` app owns callback and polling orchestration behind small protocols; Django ORM and future RAG integrations are outer adapters loaded by configuration.

**Tech Stack:** Python 3.11, Django 5.2, SQLite, pytest 9, pytest-django, Ruff, Next.js 16, React 19, TypeScript 5.9, Vitest.

## Global Constraints

- Do not add a `rag` Django app.
- Do not add extraction, OCR, chunks, embeddings, vectors, retrieval, prompts, or LLM dependencies.
- Do not add Redis, Celery, Celery Beat, cron, APScheduler, or another scheduler dependency.
- Preserve the current unauthenticated local-development boundary.
- The `documents` app must never import `document_integrations` or a future `rag` package.
- Core integration services must depend on protocols, not Django ORM classes.
- All document and outbox models must remain routed exclusively to the `documents` SQLite alias.
- Event delivery is at least once; callback implementations deduplicate by event UUID.
- Physical file paths and document content must never appear in events, API additions, or logs.
- Missing adapter settings must not prevent Django startup, migrations, document CRUD, or tests.
- Every behavior begins with a focused failing test.
- Preserve unrelated working-tree and index changes.
- Do not create commits during plan authoring. The commit commands below are execution checkpoints and should be skipped if the user keeps execution in no-commit mode.

## File Map

### Document producer

- Create `src/django/documents/contracts.py`: immutable event, claim, failure-disposition, and revision DTOs.
- Modify `src/django/documents/models.py`: add `Document.content_revision` and `DocumentOutboxEvent`.
- Create `src/django/documents/migrations/0002_document_content_revision_and_outbox.py`: schema migration.
- Create `src/django/documents/outbox.py`: append, claim, success, retry, dead-letter, requeue, and eligible-count operations.
- Create `src/django/documents/revisions.py`: read-only current revision snapshots.
- Modify `src/django/documents/services.py`: transactional lifecycle events and revision increments.
- Modify `src/django/documents/serializers.py`: expose `contentRevision`.

### Integration orchestration

- Create `src/django/document_integrations/__init__.py`.
- Create `src/django/document_integrations/apps.py`.
- Create `src/django/document_integrations/contracts.py`: indexed-state and service-report DTOs.
- Create `src/django/document_integrations/ports.py`: segregated protocols.
- Create `src/django/document_integrations/callback_service.py`: direct callback orchestration.
- Create `src/django/document_integrations/polling_service.py`: revision reconciliation.
- Create `src/django/document_integrations/adapters/__init__.py`.
- Create `src/django/document_integrations/adapters/django_documents.py`: ORM/outbox adapters and system clock.
- Create `src/django/document_integrations/adapters/import_string.py`: configured adapter loader.
- Create management command packages and the commands `dispatch_document_outbox.py` and `reconcile_document_revisions.py`.
- Modify `src/django/app/settings.py`: app registration and integration defaults.

### Tests and compatibility

- Modify `src/django/tests/test_document_database.py`.
- Modify `src/django/tests/test_document_services.py`.
- Modify `src/django/tests/test_document_api.py`.
- Create `src/django/tests/test_document_outbox.py`.
- Create `src/django/tests/test_document_callback_service.py`.
- Create `src/django/tests/test_document_polling_service.py`.
- Create `src/django/tests/test_document_integration_commands.py`.
- Create `src/django/tests/test_document_architecture.py`.
- Modify `src/frontend/app/documents/types.ts`.
- Modify `src/frontend/app/documents/lib/api.test.ts`.
- Modify `src/frontend/app/documents/components/DocumentDetail.test.tsx`.
- Modify `src/frontend/app/documents/components/DocumentLibrary.test.tsx`.
- Modify `src/frontend/app/documents/components/UploadWorkspace.test.tsx`.
- Modify `Makefile`.
- Modify `README.md`.

---

### Task 1: Add immutable contracts and the revision/outbox schema

**Files:**
- Create: `src/django/documents/contracts.py`
- Modify: `src/django/documents/models.py`
- Create: `src/django/documents/migrations/0002_document_content_revision_and_outbox.py`
- Modify: `src/django/tests/test_document_database.py`

**Interfaces:**
- Consumes: existing `Document`, the `documents` database router, and the dedicated SQLite alias.
- Produces: `DocumentEventEnvelope`, `ClaimedDocumentEvent`, `FailureDisposition`, `safe_error_code`, `DocumentRevisionSnapshot`, `Document.content_revision`, and `DocumentOutboxEvent`.

- [ ] **Step 1: Write failing schema and contract tests**

Add the standard-library imports below, replace the existing model import with
`from documents.models import Document, DocumentOutboxEvent`, and append the
tests:

```python
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from uuid import uuid4

from documents.contracts import DocumentEventEnvelope
from documents.models import Document, DocumentOutboxEvent


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
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
cd src/django
UV_CACHE_DIR=../../.uv-cache uv run pytest \
  tests/test_document_database.py::test_event_envelope_is_immutable_and_path_free \
  tests/test_document_database.py::test_document_revision_and_outbox_are_stored_in_documents_database -q
```

Expected: collection fails because `documents.contracts` and `DocumentOutboxEvent` do not exist.

- [ ] **Step 3: Create the immutable document contracts**

Create `src/django/documents/contracts.py`:

```python
import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping
from uuid import UUID


class FailureDisposition(StrEnum):
    RETRIED = "retried"
    DEAD_LETTERED = "dead_lettered"


def safe_error_code(value: str, *, fallback: str = "callback_failed") -> str:
    return value if re.fullmatch(r"[a-z][a-z0-9_]{0,99}", value) else fallback


@dataclass(frozen=True)
class DocumentEventEnvelope:
    event_id: UUID
    event_type: str
    schema_version: int
    document_id: UUID
    content_revision: int
    source_sha256: str
    payload: Mapping[str, object]
    occurred_at: datetime

    def __post_init__(self):
        object.__setattr__(
            self,
            "payload",
            MappingProxyType(dict(self.payload)),
        )


@dataclass(frozen=True)
class ClaimedDocumentEvent:
    envelope: DocumentEventEnvelope
    claim_token: UUID
    attempt_count: int


@dataclass(frozen=True)
class DocumentRevisionSnapshot:
    document_id: UUID
    content_revision: int
    source_sha256: str
    content_type: str
    size: int
    updated_at: datetime
```

- [ ] **Step 4: Add the revision and outbox models**

Add `content_revision` to `Document` and add this complete model below it in `src/django/documents/models.py`:

```python
class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    file = models.FileField(max_length=255)
    filename = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    content_type = models.CharField(max_length=127)
    size = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    content_revision = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class DocumentOutboxEvent(models.Model):
    class EventType(models.TextChoices):
        CREATED = "document.created"
        CONTENT_REPLACED = "document.content_replaced"
        METADATA_UPDATED = "document.metadata_updated"
        DELETED = "document.deleted"

    class Status(models.TextChoices):
        PENDING = "pending"
        CLAIMED = "claimed"
        DISPATCHED = "dispatched"
        DEAD_LETTER = "dead_letter"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    event_type = models.CharField(max_length=64, choices=EventType.choices)
    schema_version = models.PositiveIntegerField(default=1)
    document_id = models.UUIDField()
    content_revision = models.PositiveIntegerField()
    source_sha256 = models.CharField(max_length=64)
    payload = models.JSONField(default=dict)
    occurred_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    available_at = models.DateTimeField(auto_now_add=True)
    claim_token = models.UUIDField(null=True, blank=True)
    claim_expires_at = models.DateTimeField(null=True, blank=True)
    attempt_count = models.PositiveIntegerField(default=0)
    last_error_code = models.CharField(max_length=100, blank=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["occurred_at", "id"]
        indexes = [
            models.Index(
                fields=["status", "available_at"],
                name="doc_outbox_due_idx",
            ),
            models.Index(
                fields=["status", "claim_expires_at"],
                name="doc_outbox_lease_idx",
            ),
            models.Index(
                fields=["document_id", "content_revision"],
                name="doc_outbox_revision_idx",
            ),
            models.Index(fields=["occurred_at"], name="doc_outbox_time_idx"),
        ]
```

- [ ] **Step 5: Generate and inspect migration `0002`**

Run:

```bash
cd src/django
UV_CACHE_DIR=../../.uv-cache uv run python manage.py makemigrations documents
```

Expected: `0002_document_content_revision_and_outbox.py` adds
`Document.content_revision`, creates `DocumentOutboxEvent`, and creates exactly
the four declared indexes. Confirm it has dependency
`("documents", "0001_initial")` and contains no unrelated app operations.

- [ ] **Step 6: Run focused tests and migration checks**

Run:

```bash
cd src/django
UV_CACHE_DIR=../../.uv-cache uv run pytest tests/test_document_database.py -q
UV_CACHE_DIR=../../.uv-cache uv run python manage.py makemigrations documents --check --dry-run
```

Expected: all document database tests pass and Django reports no changes.

- [ ] **Step 7: Review checkpoint**

Review only the contracts, models, migration, and database tests. Confirm the
outbox has no foreign key to `Document` and all new ORM objects use the
`documents` alias through the existing router.

- [ ] **Step 8: Commit checkpoint**

```bash
git add \
  src/django/documents/contracts.py \
  src/django/documents/models.py \
  src/django/documents/migrations/0002_document_content_revision_and_outbox.py \
  src/django/tests/test_document_database.py
git commit -m "feat(documents): add revisioned outbox schema"
```

---

### Task 2: Append lifecycle events transactionally

**Files:**
- Create: `src/django/documents/outbox.py`
- Modify: `src/django/documents/services.py`
- Modify: `src/django/tests/test_document_services.py`

**Interfaces:**
- Consumes: `Document`, `DocumentOutboxEvent`, existing upload validation and file-compensation behavior.
- Produces: `append_document_event(...) -> DocumentOutboxEvent`; transactional created, metadata-updated, content-replaced, and deleted events.

- [ ] **Step 1: Write failing lifecycle-event tests**

Replace the existing model import with
`from documents.models import Document, DocumentOutboxEvent`, then append:

```python
def outbox_events(document_id):
    return list(
        DocumentOutboxEvent.objects.filter(document_id=document_id).order_by(
            "occurred_at",
            "id",
        )
    )


@pytest.mark.django_db(databases=["documents"])
def test_create_appends_created_event(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path

    document = create_document(SimpleUploadedFile("notes.txt", b"hello"))

    event = outbox_events(document.id)[0]
    assert event.event_type == DocumentOutboxEvent.EventType.CREATED
    assert event.content_revision == 1
    assert event.source_sha256 == document.sha256
    assert event.payload == {
        "filename": "notes.txt",
        "content_type": "text/plain",
        "size": 5,
    }


@pytest.mark.django_db(databases=["documents"])
def test_metadata_change_emits_event_without_incrementing_content_revision(
    tmp_path,
    settings,
):
    settings.MEDIA_ROOT = tmp_path
    document = create_document(SimpleUploadedFile("notes.txt", b"hello"))

    updated = update_document(document, {"title": "Knowledge", "tags": ["rag"]})

    events = outbox_events(document.id)
    assert updated.content_revision == 1
    assert [event.event_type for event in events] == [
        DocumentOutboxEvent.EventType.CREATED,
        DocumentOutboxEvent.EventType.METADATA_UPDATED,
    ]
    assert events[-1].payload == {"changed_fields": ["tags", "title"]}


@pytest.mark.django_db(databases=["documents"])
def test_noop_metadata_update_emits_no_event(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    document = create_document(SimpleUploadedFile("notes.txt", b"hello"))

    update_document(document, {"title": document.title})

    assert len(outbox_events(document.id)) == 1


@pytest.mark.django_db(databases=["documents"])
def test_replacement_increments_revision_and_emits_content_event(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    document = create_document(SimpleUploadedFile("notes.txt", b"old"))

    updated = update_document(
        document,
        {},
        SimpleUploadedFile("new.md", b"# new"),
    )

    event = outbox_events(document.id)[-1]
    assert updated.content_revision == 2
    assert event.event_type == DocumentOutboxEvent.EventType.CONTENT_REPLACED
    assert event.content_revision == 2
    assert event.source_sha256 == updated.sha256


@pytest.mark.django_db(databases=["documents"])
def test_replacement_with_metadata_change_emits_both_events(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    document = create_document(SimpleUploadedFile("notes.txt", b"old"))

    update_document(
        document,
        {"title": "Replacement"},
        SimpleUploadedFile("new.md", b"# new"),
    )

    assert [event.event_type for event in outbox_events(document.id)] == [
        DocumentOutboxEvent.EventType.CREATED,
        DocumentOutboxEvent.EventType.CONTENT_REPLACED,
        DocumentOutboxEvent.EventType.METADATA_UPDATED,
    ]


@pytest.mark.django_db(databases=["documents"])
def test_delete_event_survives_document_deletion(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    document = create_document(SimpleUploadedFile("notes.txt", b"hello"))
    document_id = document.id

    delete_document(document)

    deleted = DocumentOutboxEvent.objects.get(
        document_id=document_id,
        event_type=DocumentOutboxEvent.EventType.DELETED,
    )
    assert deleted.content_revision == 1
    assert not Document.objects.filter(pk=document_id).exists()
```

- [ ] **Step 2: Run lifecycle tests and verify RED**

Run:

```bash
cd src/django
UV_CACHE_DIR=../../.uv-cache uv run pytest \
  tests/test_document_services.py::test_create_appends_created_event \
  tests/test_document_services.py::test_metadata_change_emits_event_without_incrementing_content_revision \
  tests/test_document_services.py::test_noop_metadata_update_emits_no_event \
  tests/test_document_services.py::test_replacement_increments_revision_and_emits_content_event \
  tests/test_document_services.py::test_delete_event_survives_document_deletion -q
```

Expected: failures because document services do not append events or increment
content revisions.

- [ ] **Step 3: Implement event appending**

Create `src/django/documents/outbox.py` with this initial content:

```python
from collections.abc import Mapping
from uuid import UUID

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
```

- [ ] **Step 4: Make creation atomic with its event**

Replace `create_document` in `src/django/documents/services.py` with:

```python
def create_document(uploaded_file, *, title: str | None = None) -> Document:
    validated = validate_upload(uploaded_file)
    initial_title = title if title is not None else Path(validated.filename).stem
    metadata = _validated_metadata(
        {
            "filename": validated.filename,
            "title": initial_title,
            "description": "",
            "tags": [],
        }
    )
    document = Document(
        **metadata,
        content_type=validated.content_type,
        size=validated.size,
        sha256=validated.sha256,
    )
    document.file.save(uuid4().hex, ContentFile(validated.content), save=False)
    try:
        with transaction.atomic(using=DATABASE_ALIAS):
            document.save(using=DATABASE_ALIAS)
            append_document_event(
                event_type=DocumentOutboxEvent.EventType.CREATED,
                document_id=document.id,
                content_revision=document.content_revision,
                source_sha256=document.sha256,
                payload={
                    "filename": document.filename,
                    "content_type": document.content_type,
                    "size": document.size,
                },
            )
    except Exception:
        document.file.storage.delete(document.file.name)
        raise
    return document
```

Add these imports:

```python
from .models import Document, DocumentOutboxEvent
from .outbox import append_document_event
```

- [ ] **Step 5: Make update event-aware**

Replace `update_document` with:

```python
def update_document(
    document: Document,
    metadata: dict[str, object],
    replacement=None,
) -> Document:
    validated_file = validate_upload(replacement) if replacement is not None else None
    values = _validated_metadata(metadata)
    old_name: str | None = None
    new_name: str | None = None

    if validated_file is not None:
        new_name = document.file.storage.save(uuid4().hex, ContentFile(validated_file.content))

    try:
        with transaction.atomic(using=DATABASE_ALIAS):
            current = (
                Document.objects.using(DATABASE_ALIAS)
                .select_for_update()
                .get(pk=document.pk)
            )
            old_name = current.file.name
            changed_fields = sorted(
                field for field, value in values.items() if getattr(current, field) != value
            )
            for field in changed_fields:
                setattr(current, field, values[field])

            if validated_file is not None and new_name is not None:
                current.file.name = new_name
                current.content_type = validated_file.content_type
                current.size = validated_file.size
                current.sha256 = validated_file.sha256
                current.content_revision += 1

            if changed_fields or validated_file is not None:
                current.save(using=DATABASE_ALIAS)

            if validated_file is not None:
                append_document_event(
                    event_type=DocumentOutboxEvent.EventType.CONTENT_REPLACED,
                    document_id=current.id,
                    content_revision=current.content_revision,
                    source_sha256=current.sha256,
                    payload={
                        "filename": current.filename,
                        "content_type": current.content_type,
                        "size": current.size,
                    },
                )
            if changed_fields:
                append_document_event(
                    event_type=DocumentOutboxEvent.EventType.METADATA_UPDATED,
                    document_id=current.id,
                    content_revision=current.content_revision,
                    source_sha256=current.sha256,
                    payload={"changed_fields": changed_fields},
                )
    except Exception:
        if new_name is not None:
            document.file.storage.delete(new_name)
        raise

    if new_name is not None and old_name != new_name:
        try:
            document.file.storage.delete(old_name)
        except OSError:
            logger.error(
                "Could not remove the superseded file for document %s.",
                document.pk,
            )
    return current
```

- [ ] **Step 6: Make deletion atomic with its event and compensation**

Replace `delete_document` with:

```python
def delete_document(document: Document) -> None:
    storage = None
    storage_name = ""
    content = b""
    file_removed = False
    try:
        with transaction.atomic(using=DATABASE_ALIAS):
            current = (
                Document.objects.using(DATABASE_ALIAS)
                .select_for_update()
                .get(pk=document.pk)
            )
            storage = current.file.storage
            storage_name = current.file.name
            with storage.open(storage_name, "rb") as stored:
                content = stored.read()

            storage.delete(storage_name)
            file_removed = True
            append_document_event(
                event_type=DocumentOutboxEvent.EventType.DELETED,
                document_id=current.id,
                content_revision=current.content_revision,
                source_sha256=current.sha256,
                payload={
                    "filename": current.filename,
                    "content_type": current.content_type,
                },
            )
            current.delete(using=DATABASE_ALIAS)
    except Exception:
        if storage is not None and file_removed and not storage.exists(storage_name):
            storage.save(storage_name, ContentFile(content))
        raise
```

- [ ] **Step 7: Add forced outbox-failure compensation tests**

Append:

```python
@pytest.mark.django_db(databases=["documents"])
def test_create_removes_file_when_outbox_insert_fails(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path

    with patch(
        "documents.services.append_document_event",
        side_effect=RuntimeError("outbox unavailable"),
    ):
        with pytest.raises(RuntimeError, match="outbox unavailable"):
            create_document(SimpleUploadedFile("notes.txt", b"hello"))

    assert not Document.objects.exists()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.django_db(databases=["documents"])
def test_replace_rolls_back_record_and_new_file_when_outbox_insert_fails(
    tmp_path,
    settings,
):
    settings.MEDIA_ROOT = tmp_path
    document = create_document(SimpleUploadedFile("notes.txt", b"old"))
    old_name = document.file.name

    with patch(
        "documents.services.append_document_event",
        side_effect=RuntimeError("outbox unavailable"),
    ):
        with pytest.raises(RuntimeError, match="outbox unavailable"):
            update_document(document, {}, SimpleUploadedFile("new.md", b"# new"))

    document.refresh_from_db(using="documents")
    assert document.file.name == old_name
    assert document.content_revision == 1
    assert [path.name for path in tmp_path.iterdir()] == [old_name]


@pytest.mark.django_db(databases=["documents"])
def test_delete_restores_file_when_outbox_insert_fails(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    document = create_document(SimpleUploadedFile("notes.txt", b"hello"))
    storage_name = document.file.name

    with patch(
        "documents.services.append_document_event",
        side_effect=RuntimeError("outbox unavailable"),
    ):
        with pytest.raises(RuntimeError, match="outbox unavailable"):
            delete_document(document)

    assert Document.objects.filter(pk=document.id).exists()
    assert document.file.storage.exists(storage_name)
```

- [ ] **Step 8: Run the service suite**

Run:

```bash
cd src/django
UV_CACHE_DIR=../../.uv-cache uv run pytest tests/test_document_services.py -q
```

Expected: all service and compensation tests pass.

- [ ] **Step 9: Review checkpoint**

Confirm that each database mutation and its event share one `documents`
transaction, no-op metadata patches emit nothing, and the filesystem
compensation tests cover every outbox insertion failure.

- [ ] **Step 10: Commit checkpoint**

```bash
git add \
  src/django/documents/outbox.py \
  src/django/documents/services.py \
  src/django/tests/test_document_services.py
git commit -m "feat(documents): emit transactional lifecycle events"
```

---

### Task 3: Implement outbox leasing, retries, and dead letters

**Files:**
- Modify: `src/django/documents/outbox.py`
- Create: `src/django/tests/test_document_outbox.py`

**Interfaces:**
- Consumes: `DocumentOutboxEvent`, `DocumentEventEnvelope`, `ClaimedDocumentEvent`, and `FailureDisposition`.
- Produces: `claim_events`, `mark_dispatched`, `mark_failed`, `requeue_dead_letter`, and `count_eligible_events`.

- [ ] **Step 1: Write failing outbox state-machine tests**

Create `src/django/tests/test_document_outbox.py`:

```python
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

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
    now = datetime(2026, 7, 23, 12, tzinfo=timezone.utc)
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
    now = datetime(2026, 7, 23, 12, tzinfo=timezone.utc)
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
    now = datetime(2026, 7, 23, 12, tzinfo=timezone.utc)
    event = make_event(status=DocumentOutboxEvent.Status.CLAIMED)
    DocumentOutboxEvent.objects.filter(pk=event.pk).update(
        claim_token=uuid4(),
        claim_expires_at=now + timedelta(seconds=1),
    )

    assert claim_events(now=now, batch_size=1, lease_seconds=60) == []


@pytest.mark.django_db(databases=["documents"])
def test_stale_token_cannot_mark_event_dispatched():
    now = datetime(2026, 7, 23, 12, tzinfo=timezone.utc)
    event = make_event(available_at=now)
    claimed = claim_events(now=now, batch_size=1, lease_seconds=60)[0]

    assert mark_dispatched(event.id, uuid4(), now=now) is False
    assert mark_dispatched(event.id, claimed.claim_token, now=now) is True


@pytest.mark.django_db(databases=["documents"])
def test_failure_retries_with_bounded_backoff_then_dead_letters():
    now = datetime(2026, 7, 23, 12, tzinfo=timezone.utc)
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
    now = datetime(2026, 7, 23, 12, tzinfo=timezone.utc)
    event = make_event(status=DocumentOutboxEvent.Status.DEAD_LETTER)

    assert requeue_dead_letter(event.id, now=now) is True
    assert count_eligible_events(now=now) == 1
```

- [ ] **Step 2: Run the outbox suite and verify RED**

Run:

```bash
cd src/django
UV_CACHE_DIR=../../.uv-cache uv run pytest tests/test_document_outbox.py -q
```

Expected: import errors for the unimplemented state-machine functions.

- [ ] **Step 3: Implement outbox conversion and claiming**

Extend `src/django/documents/outbox.py` with these imports and functions:

```python
from datetime import datetime, timedelta
from types import MappingProxyType
from uuid import uuid4

from django.db import transaction
from django.db.models import F, Q

from .contracts import (
    ClaimedDocumentEvent,
    DocumentEventEnvelope,
    FailureDisposition,
    safe_error_code,
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
```

- [ ] **Step 4: Implement success, retry, dead-letter, and requeue**

Add:

```python
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
```

- [ ] **Step 5: Run tests and lint**

Run:

```bash
cd src/django
UV_CACHE_DIR=../../.uv-cache uv run pytest tests/test_document_outbox.py -q
UV_CACHE_DIR=../../.uv-cache uv run ruff check \
  documents/contracts.py documents/models.py documents/outbox.py \
  tests/test_document_outbox.py
```

Expected: all outbox tests and Ruff pass.

- [ ] **Step 6: Review checkpoint**

Verify eligibility uses a compare-and-update guard, stale claim tokens cannot
mutate state, retry delay is capped at 15 minutes, and attempt eight
dead-letters.

- [ ] **Step 7: Commit checkpoint**

```bash
git add src/django/documents/outbox.py src/django/tests/test_document_outbox.py
git commit -m "feat(documents): add reliable outbox delivery state"
```

---

### Task 4: Implement segregated integration ports and callback service

**Files:**
- Create: `src/django/document_integrations/__init__.py`
- Create: `src/django/document_integrations/apps.py`
- Create: `src/django/document_integrations/contracts.py`
- Create: `src/django/document_integrations/ports.py`
- Create: `src/django/document_integrations/callback_service.py`
- Create: `src/django/tests/test_document_callback_service.py`

**Interfaces:**
- Consumes: immutable contracts from `documents.contracts`.
- Produces: `OutboxPort`, `DocumentEventCallback`, `Clock`, `CallbackDeliveryError`, `DispatchReport`, and `DirectCallbackService.dispatch_once()`.

- [ ] **Step 1: Write callback service tests with protocol fakes**

Create `src/django/tests/test_document_callback_service.py`:

```python
from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

from document_integrations.callback_service import DirectCallbackService
from document_integrations.ports import CallbackDeliveryError
from documents.contracts import (
    ClaimedDocumentEvent,
    DocumentEventEnvelope,
    FailureDisposition,
)


NOW = datetime(2026, 7, 23, 12, tzinfo=timezone.utc)


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
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
cd src/django
UV_CACHE_DIR=../../.uv-cache uv run pytest tests/test_document_callback_service.py -q
```

Expected: collection fails because `document_integrations` does not exist.

- [ ] **Step 3: Create the integration app and service contracts**

Create an empty `src/django/document_integrations/__init__.py`.

Create `src/django/document_integrations/apps.py`:

```python
from django.apps import AppConfig


class DocumentIntegrationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "document_integrations"
```

Create `src/django/document_integrations/contracts.py`:

```python
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class DispatchReport:
    claimed: int
    dispatched: int
    retried: int
    dead_lettered: int


@dataclass(frozen=True)
class IndexedDocumentRevision:
    document_id: UUID
    content_revision: int
    source_sha256: str
    source_updated_at: datetime


@dataclass(frozen=True)
class ReconciliationReport:
    source_count: int
    indexed_count: int
    requested_sync: int
    requested_delete: int
    current: int
    failed: int
```

- [ ] **Step 4: Define segregated protocols**

Create `src/django/document_integrations/ports.py`:

```python
from datetime import datetime
from typing import Protocol, Sequence
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
```

- [ ] **Step 5: Implement callback orchestration**

Create `src/django/document_integrations/callback_service.py`:

```python
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
```

- [ ] **Step 6: Run tests and lint**

Run:

```bash
cd src/django
UV_CACHE_DIR=../../.uv-cache uv run pytest tests/test_document_callback_service.py -q
UV_CACHE_DIR=../../.uv-cache uv run ruff check \
  document_integrations/contracts.py \
  document_integrations/ports.py \
  document_integrations/callback_service.py \
  tests/test_document_callback_service.py
```

Expected: callback tests and Ruff pass without Django database access.

- [ ] **Step 7: Review checkpoint**

Confirm the callback service imports no Django ORM module and its test uses only
protocol fakes.

- [ ] **Step 8: Commit checkpoint**

```bash
git add src/django/document_integrations src/django/tests/test_document_callback_service.py
git commit -m "feat(integrations): add direct document callback service"
```

---

### Task 5: Implement revision snapshots and polling reconciliation

**Files:**
- Create: `src/django/documents/revisions.py`
- Create: `src/django/document_integrations/polling_service.py`
- Create: `src/django/tests/test_document_polling_service.py`
- Modify: `src/django/tests/test_document_database.py`

**Interfaces:**
- Consumes: `DocumentRevisionSnapshot`, `IndexedDocumentRevision`, and the three polling ports.
- Produces: `list_document_revisions()`, `RevisionPollingService.reconcile(dry_run=False)`, and `ReconciliationReport`.

- [ ] **Step 1: Write failing pure polling tests**

Create `src/django/tests/test_document_polling_service.py`:

```python
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from document_integrations.contracts import IndexedDocumentRevision
from document_integrations.polling_service import RevisionPollingService
from documents.contracts import DocumentRevisionSnapshot


NOW = datetime(2026, 7, 23, 12, tzinfo=timezone.utc)


def source(document_id, revision=1, checksum="a", updated_at=NOW):
    return DocumentRevisionSnapshot(
        document_id=document_id,
        content_revision=revision,
        source_sha256=checksum * 64,
        content_type="text/plain",
        size=5,
        updated_at=updated_at,
    )


def indexed(document_id, revision=1, checksum="a", updated_at=NOW):
    return IndexedDocumentRevision(
        document_id=document_id,
        content_revision=revision,
        source_sha256=checksum * 64,
        source_updated_at=updated_at,
    )


class FakeDocuments:
    def __init__(self, values):
        self.values = values

    def list_current(self):
        return self.values


class FakeRagState:
    def __init__(self, values):
        self.values = values

    def list_indexed(self):
        return self.values


class FakeSink:
    def __init__(self, fail_ids=None):
        self.fail_ids = set(fail_ids or [])
        self.synced = []
        self.deleted = []

    def request_sync(self, snapshot):
        if snapshot.document_id in self.fail_ids:
            raise RuntimeError("sync failed")
        self.synced.append(snapshot.document_id)

    def request_delete(self, document_id):
        if document_id in self.fail_ids:
            raise RuntimeError("delete failed")
        self.deleted.append(document_id)


def test_reconciles_missing_stale_current_metadata_and_deleted_documents():
    missing = uuid4()
    stale = uuid4()
    metadata_stale = uuid4()
    current = uuid4()
    deleted = uuid4()
    sources = [
        source(missing),
        source(stale, revision=2, checksum="b"),
        source(metadata_stale, updated_at=NOW + timedelta(minutes=1)),
        source(current),
    ]
    indexed_values = [
        indexed(stale),
        indexed(metadata_stale),
        indexed(current),
        indexed(deleted),
    ]
    sink = FakeSink()
    service = RevisionPollingService(
        documents=FakeDocuments(sources),
        rag_state=FakeRagState(indexed_values),
        commands=sink,
    )

    report = service.reconcile()

    assert set(sink.synced) == {missing, stale, metadata_stale}
    assert sink.deleted == [deleted]
    assert report.requested_sync == 3
    assert report.requested_delete == 1
    assert report.current == 1
    assert report.failed == 0


def test_dry_run_reports_without_invoking_sink_and_collects_item_failures():
    first = uuid4()
    second = uuid4()
    sink = FakeSink(fail_ids={second})
    service = RevisionPollingService(
        documents=FakeDocuments([source(first), source(second)]),
        rag_state=FakeRagState([]),
        commands=sink,
    )

    dry = service.reconcile(dry_run=True)
    actual = service.reconcile()

    assert dry.requested_sync == 2
    assert sink.synced == [first]
    assert actual.failed == 1
```

- [ ] **Step 2: Run polling tests and verify RED**

Run:

```bash
cd src/django
UV_CACHE_DIR=../../.uv-cache uv run pytest tests/test_document_polling_service.py -q
```

Expected: import failure because `polling_service.py` does not exist.

- [ ] **Step 3: Implement the pure reconciliation service**

Create `src/django/document_integrations/polling_service.py`:

```python
import logging

from .contracts import ReconciliationReport
from .ports import (
    DocumentRevisionRepository,
    RagRevisionStateReader,
    RagSyncCommandSink,
)

logger = logging.getLogger(__name__)


class RevisionPollingService:
    def __init__(
        self,
        *,
        documents: DocumentRevisionRepository,
        rag_state: RagRevisionStateReader,
        commands: RagSyncCommandSink,
    ):
        self.documents = documents
        self.rag_state = rag_state
        self.commands = commands

    def reconcile(self, *, dry_run: bool = False) -> ReconciliationReport:
        sources = {item.document_id: item for item in self.documents.list_current()}
        indexed = {item.document_id: item for item in self.rag_state.list_indexed()}
        requested_sync = 0
        requested_delete = 0
        current = 0
        failed = 0

        for document_id in sorted(sources, key=str):
            snapshot = sources[document_id]
            indexed_revision = indexed.get(document_id)
            needs_sync = indexed_revision is None or (
                indexed_revision.content_revision != snapshot.content_revision
                or indexed_revision.source_sha256 != snapshot.source_sha256
                or indexed_revision.source_updated_at != snapshot.updated_at
            )
            if not needs_sync:
                current += 1
                continue
            requested_sync += 1
            if dry_run:
                continue
            try:
                self.commands.request_sync(snapshot)
            except Exception:
                failed += 1
                logger.error(
                    "Document synchronization request failed for %s.",
                    document_id,
                )

        for document_id in sorted(set(indexed) - set(sources), key=str):
            requested_delete += 1
            if dry_run:
                continue
            try:
                self.commands.request_delete(document_id)
            except Exception:
                failed += 1
                logger.error(
                    "Document deletion request failed for %s.",
                    document_id,
                )

        return ReconciliationReport(
            source_count=len(sources),
            indexed_count=len(indexed),
            requested_sync=requested_sync,
            requested_delete=requested_delete,
            current=current,
            failed=failed,
        )
```

- [ ] **Step 4: Write a failing document revision query test**

Append to `src/django/tests/test_document_database.py`:

```python
from documents.revisions import list_document_revisions


@pytest.mark.django_db(databases=["documents"])
def test_revision_query_returns_path_free_snapshots():
    document = Document.objects.create(
        file="private-storage-name",
        filename="report.txt",
        title="report",
        content_type="text/plain",
        size=6,
        sha256="0" * 64,
        content_revision=3,
    )

    snapshot = list_document_revisions()[0]

    assert snapshot.document_id == document.id
    assert snapshot.content_revision == 3
    assert snapshot.source_sha256 == document.sha256
    assert "file" not in snapshot.__dict__
```

- [ ] **Step 5: Implement the document revision query**

Create `src/django/documents/revisions.py`:

```python
from .contracts import DocumentRevisionSnapshot
from .models import Document

DATABASE_ALIAS = "documents"


def list_document_revisions() -> list[DocumentRevisionSnapshot]:
    documents = (
        Document.objects.using(DATABASE_ALIAS)
        .only(
            "id",
            "content_revision",
            "sha256",
            "content_type",
            "size",
            "updated_at",
        )
        .order_by("id")
    )
    return [
        DocumentRevisionSnapshot(
            document_id=document.id,
            content_revision=document.content_revision,
            source_sha256=document.sha256,
            content_type=document.content_type,
            size=document.size,
            updated_at=document.updated_at,
        )
        for document in documents
    ]
```

- [ ] **Step 6: Run polling and revision tests**

Run:

```bash
cd src/django
UV_CACHE_DIR=../../.uv-cache uv run pytest \
  tests/test_document_polling_service.py \
  tests/test_document_database.py -q
```

Expected: all tests pass.

- [ ] **Step 7: Review checkpoint**

Confirm polling is pure orchestration, does not edit documents or outbox state,
detects metadata changes via `updated_at`, and continues after per-document
command failures.

- [ ] **Step 8: Commit checkpoint**

```bash
git add \
  src/django/documents/revisions.py \
  src/django/document_integrations/polling_service.py \
  src/django/tests/test_document_polling_service.py \
  src/django/tests/test_document_database.py
git commit -m "feat(integrations): add document revision reconciliation"
```

---

### Task 6: Add Django adapters and configuration

**Files:**
- Create: `src/django/document_integrations/adapters/__init__.py`
- Create: `src/django/document_integrations/adapters/django_documents.py`
- Create: `src/django/document_integrations/adapters/import_string.py`
- Modify: `src/django/app/settings.py`
- Create: `src/django/tests/test_document_integration_adapters.py`

**Interfaces:**
- Consumes: public outbox/revision functions and integration protocols.
- Produces: `DjangoOutboxAdapter`, `DjangoDocumentRevisionRepository`, `SystemClock`, `load_configured_adapter`.

- [ ] **Step 1: Write failing adapter tests**

Create `src/django/tests/test_document_integration_adapters.py`:

```python
import pytest
from django.core.exceptions import ImproperlyConfigured

from document_integrations.adapters.django_documents import (
    DjangoDocumentRevisionRepository,
    SystemClock,
)
from document_integrations.adapters.import_string import load_configured_adapter


class ConfiguredAdapter:
    def handle(self, event):
        return None


def test_loader_constructs_configured_adapter(settings):
    settings.TEST_DOCUMENT_ADAPTER = f"{__name__}.ConfiguredAdapter"

    loaded = load_configured_adapter(
        "TEST_DOCUMENT_ADAPTER",
        required_methods=("handle",),
    )

    assert isinstance(loaded, ConfiguredAdapter)


def test_loader_rejects_missing_setting(settings):
    settings.TEST_DOCUMENT_ADAPTER = ""

    with pytest.raises(ImproperlyConfigured, match="TEST_DOCUMENT_ADAPTER"):
        load_configured_adapter(
            "TEST_DOCUMENT_ADAPTER",
            required_methods=("handle",),
        )


def test_system_clock_returns_aware_utc_time():
    assert SystemClock().now().tzinfo is not None


@pytest.mark.django_db(databases=["documents"])
def test_django_revision_repository_uses_public_revision_query():
    assert DjangoDocumentRevisionRepository().list_current() == []
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
cd src/django
UV_CACHE_DIR=../../.uv-cache uv run pytest tests/test_document_integration_adapters.py -q
```

Expected: imports fail because adapter modules do not exist.

- [ ] **Step 3: Implement Django document adapters**

Create an empty `src/django/document_integrations/adapters/__init__.py`.

Create `src/django/document_integrations/adapters/django_documents.py`:

```python
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
```

- [ ] **Step 4: Implement safe configured adapter loading**

Create `src/django/document_integrations/adapters/import_string.py`:

```python
from collections.abc import Sequence

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string


def load_configured_adapter(
    setting_name: str,
    *,
    required_methods: Sequence[str],
):
    dotted_path = getattr(settings, setting_name, "")
    if not isinstance(dotted_path, str) or not dotted_path.strip():
        raise ImproperlyConfigured(f"{setting_name} must be configured.")
    try:
        adapter_class = import_string(dotted_path)
        adapter = adapter_class()
    except (ImportError, AttributeError, TypeError) as error:
        raise ImproperlyConfigured(
            f"{setting_name} does not identify a constructible adapter."
        ) from error
    missing = [name for name in required_methods if not callable(getattr(adapter, name, None))]
    if missing:
        joined = ", ".join(missing)
        raise ImproperlyConfigured(
            f"{setting_name} adapter is missing required methods: {joined}."
        )
    return adapter
```

- [ ] **Step 5: Register the integration app and defaults**

Add `"document_integrations"` immediately after `"documents"` in
`INSTALLED_APPS` and add:

```python
DOCUMENT_EVENT_CALLBACK = os.getenv("DOCUMENT_EVENT_CALLBACK", "")
DOCUMENT_RAG_REVISION_STATE_READER = os.getenv(
    "DOCUMENT_RAG_REVISION_STATE_READER",
    "",
)
DOCUMENT_RAG_SYNC_COMMAND_SINK = os.getenv("DOCUMENT_RAG_SYNC_COMMAND_SINK", "")
DOCUMENT_OUTBOX_BATCH_SIZE = int(os.getenv("DOCUMENT_OUTBOX_BATCH_SIZE", "50"))
DOCUMENT_OUTBOX_LEASE_SECONDS = int(
    os.getenv("DOCUMENT_OUTBOX_LEASE_SECONDS", "60")
)
DOCUMENT_OUTBOX_MAX_ATTEMPTS = int(
    os.getenv("DOCUMENT_OUTBOX_MAX_ATTEMPTS", "8")
)
```

Do not import adapters or validate dotted paths during settings import.

- [ ] **Step 6: Run adapter tests and Django checks**

Run:

```bash
cd src/django
UV_CACHE_DIR=../../.uv-cache uv run pytest tests/test_document_integration_adapters.py -q
UV_CACHE_DIR=../../.uv-cache uv run python manage.py check
```

Expected: tests and Django system checks pass with all adapter settings empty.

- [ ] **Step 7: Review checkpoint**

Confirm adapter configuration is lazy and document CRUD can start without any
future RAG class.

- [ ] **Step 8: Commit checkpoint**

```bash
git add \
  src/django/document_integrations/adapters \
  src/django/app/settings.py \
  src/django/tests/test_document_integration_adapters.py
git commit -m "feat(integrations): add Django document adapters"
```

---

### Task 7: Add dispatch and reconciliation management commands

**Files:**
- Create: `src/django/document_integrations/management/__init__.py`
- Create: `src/django/document_integrations/management/commands/__init__.py`
- Create: `src/django/document_integrations/management/commands/dispatch_document_outbox.py`
- Create: `src/django/document_integrations/management/commands/reconcile_document_revisions.py`
- Create: `src/django/tests/test_document_integration_commands.py`

**Interfaces:**
- Consumes: configured adapters, Django adapters, callback service, polling service, and settings defaults.
- Produces: one-shot, scheduler-neutral commands with dry-run and structured summaries.

- [ ] **Step 1: Write failing command tests**

Create `src/django/tests/test_document_integration_commands.py`:

```python
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
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
cd src/django
UV_CACHE_DIR=../../.uv-cache uv run pytest tests/test_document_integration_commands.py -q
```

Expected: unknown management-command failures.

- [ ] **Step 3: Implement the dispatch command**

Create empty package files:

```text
src/django/document_integrations/management/__init__.py
src/django/document_integrations/management/commands/__init__.py
```

Create `dispatch_document_outbox.py`:

```python
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
```

- [ ] **Step 4: Implement the reconciliation command**

Create `reconcile_document_revisions.py`:

```python
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
```

- [ ] **Step 5: Run command tests and manual dry runs**

Run:

```bash
cd src/django
UV_CACHE_DIR=../../.uv-cache uv run pytest tests/test_document_integration_commands.py -q
UV_CACHE_DIR=../../.uv-cache uv run python manage.py dispatch_document_outbox --dry-run
```

Expected: tests pass and the manual command prints `eligible=<number>` without
requiring adapter configuration.

- [ ] **Step 6: Review checkpoint**

Confirm both commands perform one bounded run, do not install a scheduler, and
load future RAG classes only when invoked.

- [ ] **Step 7: Commit checkpoint**

```bash
git add \
  src/django/document_integrations/management \
  src/django/tests/test_document_integration_commands.py
git commit -m "feat(integrations): add document workflow commands"
```

---

### Task 8: Preserve API and frontend compatibility

**Files:**
- Modify: `src/django/documents/serializers.py`
- Modify: `src/django/tests/test_document_api.py`
- Modify: `src/frontend/app/documents/types.ts`
- Modify: `src/frontend/app/documents/lib/api.test.ts`
- Modify: `src/frontend/app/documents/components/DocumentDetail.test.tsx`
- Modify: `src/frontend/app/documents/components/DocumentLibrary.test.tsx`
- Modify: `src/frontend/app/documents/components/UploadWorkspace.test.tsx`

**Interfaces:**
- Consumes: `Document.content_revision`.
- Produces: additive JSON field `contentRevision: number` and matching TypeScript type.

- [ ] **Step 1: Write failing API revision assertion**

In `test_post_upload_then_get_list`, add:

```python
assert created["contentRevision"] == 1
assert listed[0]["contentRevision"] == 1
```

In `test_multipart_patch_replaces_file`, add:

```python
assert response.json()["contentRevision"] == 2
```

- [ ] **Step 2: Run focused API tests and verify RED**

Run:

```bash
cd src/django
UV_CACHE_DIR=../../.uv-cache uv run pytest \
  tests/test_document_api.py::test_post_upload_then_get_list \
  tests/test_document_api.py::test_multipart_patch_replaces_file -q
```

Expected: `KeyError` for `contentRevision`.

- [ ] **Step 3: Serialize the revision**

Add this entry after `"sha256"` in `serialize_document`:

```python
"contentRevision": document.content_revision,
```

- [ ] **Step 4: Update the frontend contract and fixture**

Add to `DocumentRecord` after `sha256`:

```typescript
contentRevision: number;
```

Add to `documentFixture` in `api.test.ts`, to `documentFixture` in both
component test files, and to `uploadedDocument` in
`UploadWorkspace.test.tsx`:

```typescript
contentRevision: 1,
```

- [ ] **Step 5: Run backend API, frontend API, and type checks**

Run:

```bash
cd src/django
UV_CACHE_DIR=../../.uv-cache uv run pytest tests/test_document_api.py -q
cd ../frontend
/Users/noshysmiles/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
  node_modules/vitest/vitest.mjs run app/documents/lib/api.test.ts
/Users/noshysmiles/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
  node_modules/typescript/bin/tsc --noEmit
```

Expected: document API tests, frontend API tests, and TypeScript pass.

- [ ] **Step 6: Review checkpoint**

Confirm this is an additive API change and no existing URL, mutation, or
frontend behavior changed.

- [ ] **Step 7: Commit checkpoint**

```bash
git add \
  src/django/documents/serializers.py \
  src/django/tests/test_document_api.py \
  src/frontend/app/documents/types.ts \
  src/frontend/app/documents/lib/api.test.ts \
  src/frontend/app/documents/components/DocumentDetail.test.tsx \
  src/frontend/app/documents/components/DocumentLibrary.test.tsx \
  src/frontend/app/documents/components/UploadWorkspace.test.tsx
git commit -m "feat(documents): expose content revision"
```

---

### Task 9: Enforce architecture and document scheduling hooks

**Files:**
- Create: `src/django/tests/test_document_architecture.py`
- Modify: `Makefile`
- Modify: `README.md`

**Interfaces:**
- Consumes: completed producer and integration packages.
- Produces: executable import-boundary tests, Make targets, and scheduler-neutral operational documentation.

- [ ] **Step 1: Write architecture-boundary tests**

Create `src/django/tests/test_document_architecture.py`:

```python
import ast
from pathlib import Path


DJANGO_ROOT = Path(__file__).resolve().parents[1]


def imported_roots(path):
    tree = ast.parse(path.read_text(), filename=str(path))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def test_documents_never_imports_integration_or_rag_packages():
    forbidden = {"document_integrations", "rag"}

    for path in (DJANGO_ROOT / "documents").rglob("*.py"):
        assert imported_roots(path).isdisjoint(forbidden), path


def test_core_integration_services_do_not_import_django_orm():
    core_files = [
        DJANGO_ROOT / "document_integrations" / "contracts.py",
        DJANGO_ROOT / "document_integrations" / "ports.py",
        DJANGO_ROOT / "document_integrations" / "callback_service.py",
        DJANGO_ROOT / "document_integrations" / "polling_service.py",
    ]

    for path in core_files:
        assert "django" not in imported_roots(path), path
```

- [ ] **Step 2: Run the architecture tests**

Run:

```bash
cd src/django
UV_CACHE_DIR=../../.uv-cache uv run pytest tests/test_document_architecture.py -q
```

Expected: both boundary tests pass.

- [ ] **Step 3: Add scheduler-neutral Make targets**

Add to `.PHONY`:

```make
.PHONY: dispatch-document-outbox reconcile-document-revisions
```

Add:

```make
dispatch-document-outbox:
	$(COMPOSE) $(DEV_FILES) exec django python manage.py dispatch_document_outbox

reconcile-document-revisions:
	$(COMPOSE) $(DEV_FILES) exec django python manage.py reconcile_document_revisions
```

- [ ] **Step 4: Document adapter contracts and scheduling examples**

Add a `### Document integration workflows` section to `README.md` containing:

````markdown
### Document integration workflows

The document app records lifecycle changes in its own transactional outbox.
It does not import or require a RAG implementation.

Configure future adapters with:

- `DOCUMENT_EVENT_CALLBACK`: class implementing `handle(event)`.
- `DOCUMENT_RAG_REVISION_STATE_READER`: class implementing `list_indexed()`.
- `DOCUMENT_RAG_SYNC_COMMAND_SINK`: class implementing
  `request_sync(snapshot)` and `request_delete(document_id)`.

Run one callback batch:

```sh
make dispatch-document-outbox
```

Run one revision reconciliation pass:

```sh
make reconcile-document-revisions
```

These commands intentionally run once. Schedule them with the deployment
system selected for the future RAG application. Callback delivery is
at-least-once, so consumers must deduplicate by event UUID. Revision
reconciliation is an independent consistency repair mechanism.
````

- [ ] **Step 5: Run architecture, command, and Makefile checks**

Run:

```bash
cd src/django
UV_CACHE_DIR=../../.uv-cache uv run pytest \
  tests/test_document_architecture.py \
  tests/test_document_integration_commands.py -q
cd ../..
make -n dispatch-document-outbox
make -n reconcile-document-revisions
```

Expected: tests pass and both dry Make invocations print the intended Compose
management commands without executing them.

- [ ] **Step 6: Review checkpoint**

Confirm documentation does not select a scheduler or claim a RAG app exists,
and architecture tests enforce the approved dependency direction.

- [ ] **Step 7: Commit checkpoint**

```bash
git add src/django/tests/test_document_architecture.py Makefile README.md
git commit -m "docs(documents): add integration workflow operations"
```

---

### Task 10: Complete regression and production verification

**Files:**
- Verify all files listed above.
- Modify only files that fail an in-scope check; preserve unrelated dirty files.

**Interfaces:**
- Consumes: all completed tasks.
- Produces: fresh evidence that the producer, integration services, frontend contract, migrations, and Compose stack work independently.

- [ ] **Step 1: Run the complete Django suite**

Run:

```bash
cd src/django
UV_CACHE_DIR=../../.uv-cache uv run pytest tests -q
```

Expected: every Django test passes. If unrelated pre-existing tests fail, record
their exact names and rerun the complete document scope:

```bash
UV_CACHE_DIR=../../.uv-cache uv run pytest \
  tests/test_document_database.py \
  tests/test_document_validation.py \
  tests/test_document_services.py \
  tests/test_document_api.py \
  tests/test_document_outbox.py \
  tests/test_document_callback_service.py \
  tests/test_document_polling_service.py \
  tests/test_document_integration_adapters.py \
  tests/test_document_integration_commands.py \
  tests/test_document_architecture.py -q
```

- [ ] **Step 2: Run scoped Ruff and Django checks**

Run:

```bash
cd src/django
UV_CACHE_DIR=../../.uv-cache uv run ruff check \
  documents \
  document_integrations \
  tests/test_document_database.py \
  tests/test_document_services.py \
  tests/test_document_api.py \
  tests/test_document_outbox.py \
  tests/test_document_callback_service.py \
  tests/test_document_polling_service.py \
  tests/test_document_integration_adapters.py \
  tests/test_document_integration_commands.py \
  tests/test_document_architecture.py
UV_CACHE_DIR=../../.uv-cache uv run python manage.py check
UV_CACHE_DIR=../../.uv-cache uv run python manage.py makemigrations documents --check --dry-run
```

Expected: Ruff and Django checks pass, with no pending document migration.

- [ ] **Step 3: Apply and verify the dedicated database migration**

Run through the running Compose service:

```bash
docker compose exec -T django python manage.py migrate --database=documents
docker compose exec -T django python manage.py migrate --database=documents --check
```

Expected: migration `documents.0002...` applies and the check exits zero.

- [ ] **Step 4: Run document frontend tests and TypeScript**

Run:

```bash
cd src/frontend
/Users/noshysmiles/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
  node_modules/vitest/vitest.mjs run app/documents
/Users/noshysmiles/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
  node_modules/typescript/bin/tsc --noEmit
```

Expected: every document frontend test and TypeScript pass. The known unrelated
chat-workspace frontend failures remain outside this feature gate unless the
user expands scope.

- [ ] **Step 5: Run the production Next.js build**

Run:

```bash
cd src/frontend
/Users/noshysmiles/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
  node_modules/next/dist/bin/next build
```

Expected: compilation and TypeScript pass and the existing document routes are
listed.

- [ ] **Step 6: Validate all Compose overlays**

Run:

```bash
cd ../..
docker compose -f docker-compose.yml -f docker-compose.dev.yml config -q
docker compose -f docker-compose.yml -f docker-compose.staging.yml config -q
docker compose -f docker-compose.yml -f docker-compose.prod.yml config -q
```

Expected: all three commands exit zero.

- [ ] **Step 7: Smoke-test commands without RAG adapters**

Run:

```bash
docker compose exec -T django python manage.py dispatch_document_outbox --dry-run
docker compose exec -T django python manage.py reconcile_document_revisions --dry-run
```

Expected: dispatch prints an eligible count. Reconciliation returns the
documented configuration error until
`DOCUMENT_RAG_REVISION_STATE_READER` is supplied; Django itself remains
healthy.

- [ ] **Step 8: Inspect final state**

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors. Confirm all unrelated staged, modified, and
untracked paths are unchanged.

- [ ] **Step 9: Final review checkpoint**

Review against
`docs/superpowers/specs/2026-07-23-document-rag-readiness-design.md`. Confirm:

- Documents creates durable events without downstream availability.
- Callback delivery is at least once with safe retry/dead-letter handling.
- Polling independently repairs missing, stale, metadata-changed, and deleted
  downstream state.
- Neither producer nor orchestration contains a RAG feature or provider.
- Both orchestration services pass using fakes without Django ORM imports.

- [ ] **Step 10: Commit checkpoint**

If execution is authorized to commit:

```bash
git add \
  src/django/documents \
  src/django/document_integrations \
  src/django/tests/test_document_*.py \
  src/frontend/app/documents \
  src/django/app/settings.py \
  Makefile \
  README.md \
  docs/superpowers/specs/2026-07-23-document-rag-readiness-design.md \
  docs/superpowers/plans/2026-07-23-document-rag-readiness.md
git commit -m "feat(documents): add RAG integration workflows"
```

If execution remains in no-commit mode, skip this step and hand off the verified
working tree unchanged.
