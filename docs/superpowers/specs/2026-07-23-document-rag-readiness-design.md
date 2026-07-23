# Document RAG Readiness Design

## Purpose

Prepare the Django document library for reliable downstream RAG integration
without adding extraction, chunking, embeddings, vector storage, retrieval, an
LLM provider, or a `rag` Django app.

The document app remains the authoritative repository for uploaded files and
metadata. It publishes durable, versioned lifecycle events. A separate
`document_integrations` app provides complete callback-dispatch and scheduled
revision-reconciliation services whose RAG-specific dependencies are supplied
through interfaces.

## Scope

### Included

- Add a monotonic content revision to every document.
- Record document lifecycle events in the document SQLite database within the
  same transaction as the associated document mutation.
- Support created, content-replaced, metadata-updated, and deleted events.
- Provide atomic outbox claiming, expiring leases, retry scheduling, bounded
  exponential backoff, and dead-letter handling.
- Implement an at-least-once direct-callback dispatcher.
- Implement revision reconciliation that detects documents that are missing,
  stale, current, or deleted in a downstream index.
- Provide scheduler-neutral Django management commands for dispatch and
  reconciliation.
- Load downstream adapters through configuration and dependency injection.
- Preserve existing document API and Next.js behavior.
- Expose the current content revision in document API responses.
- Test every component independently without Redis, a scheduler, a callback
  endpoint, or a RAG application.

### Excluded

- A `rag` Django app.
- File-text extraction and OCR.
- Chunk creation or storage.
- Embedding generation.
- Vector databases or `pgvector`.
- Retrieval, reranking, prompt construction, or LLM calls.
- Celery, Celery Beat, cron installation, or another scheduler runtime.
- HTTP callback transport.
- Authentication and authorization, which remain deferred as documented by
  the existing document-library design.

## Architecture

### Dependency direction

The system has three conceptual layers:

```text
documents <- document_integrations <- future rag adapters
```

The `documents` app owns files, metadata, revisions, and its transactional
outbox. It does not import `document_integrations` or a future `rag` package.

The `document_integrations` app owns orchestration for callback delivery and
revision reconciliation. Its core services depend on small protocols rather
than Django models or future RAG classes. Infrastructure adapters connect those
protocols to the document ORM and configured downstream classes.

A future RAG app implements callback, indexed-revision-state, and synchronization
command protocols. It owns every extraction and retrieval concern.

### Django applications

`documents` remains routed exclusively to the `documents` SQLite database.
`DocumentOutboxEvent` belongs to that app, so its insertion can share the same
database transaction as `Document`.

`document_integrations` has no models and owns no database. It may read or
mutate outbox delivery state only through public document adapters. This keeps
its services independently testable and avoids creating a third persistence
boundary.

## SOLID boundaries

### Single responsibility

- Document services validate and persist document lifecycle changes.
- The outbox module appends and manages outbox delivery state.
- The revision module returns immutable document revision snapshots.
- The callback service dispatches claimed events.
- The polling service compares source and indexed revision state.
- Management commands translate configuration and CLI inputs into service
  invocations.

### Open/closed

New callback transports, RAG stores, or schedulers are introduced as adapters.
They do not require changes to document mutation or orchestration logic.

### Liskov substitution

Production adapters and test fakes implement the same typed protocols. Shared
contract tests verify equivalent observable behavior where applicable.

### Interface segregation

The integration layer defines separate protocols for:

- Outbox event claims and delivery-state updates.
- Direct event callbacks.
- Document revision snapshots.
- Indexed RAG revision reads.
- RAG synchronization commands.
- Time.

No consumer must implement methods it does not use.

### Dependency inversion

Callback and polling services depend only on protocols and immutable DTOs.
Django ORM access and configurable future-RAG classes are adapters at the
outside of the integration layer.

## Data model

### Document content revision

`Document` gains:

```text
content_revision: positive integer, default 1
```

Existing records migrate to revision `1`.

Creation stores revision `1`. Metadata-only updates preserve the revision. A
successful physical-file replacement increments it exactly once while holding
the current document row for update. The revision and SHA-256 together identify
the current source bytes.

### DocumentOutboxEvent

The outbox record contains immutable event data and mutable relay state:

```text
id: UUID event identifier
event_type: constrained lifecycle event name
schema_version: positive integer, initially 1
document_id: plain UUID, not a foreign key
content_revision: positive integer
source_sha256: 64-character checksum
payload: minimal JSON object
occurred_at: event creation time
status: pending, claimed, dispatched, or dead_letter
available_at: earliest eligible delivery time
claim_token: nullable UUID
claim_expires_at: nullable timestamp
attempt_count: non-negative integer
last_error_code: bounded safe machine-readable string
dispatched_at: nullable timestamp
```

`document_id` is deliberately not a foreign key. A deletion event must survive
deletion of the associated document.

Database indexes support:

- `status` plus `available_at`.
- `status` plus `claim_expires_at`.
- `document_id` plus `content_revision`.
- `occurred_at`.

Event payloads never contain physical storage paths or document contents.

## Public contracts

The document app publishes immutable dataclasses:

```python
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


@dataclass(frozen=True)
class DocumentRevisionSnapshot:
    document_id: UUID
    content_revision: int
    source_sha256: str
    content_type: str
    size: int
    updated_at: datetime
```

The envelope is the callback idempotency boundary. Downstream callbacks must
deduplicate by `event_id`.

The revision snapshot contains only information required to compare source
content with downstream indexing state. It does not expose file paths or bytes.

## Lifecycle events

The initial schema version supports:

- `document.created`
- `document.content_replaced`
- `document.metadata_updated`
- `document.deleted`

Created and replacement payloads include validated filename, content type, and
size. Metadata-update payloads include the names of fields that changed, not
document contents. Deleted payloads contain only the final validated filename
and content type required for audit context.

Event schema versioning allows payload evolution without changing event names.
Consumers must reject unsupported schema versions with a safe error code.

## Document mutation workflow

### Creation

1. Validate the upload and metadata.
2. Write the UUID-named physical file.
3. Start a transaction on the `documents` alias.
4. Insert `Document` at revision `1`.
5. Append `document.created`.
6. Commit.
7. If persistence fails, remove the newly written file.

### Metadata update

1. Validate requested metadata.
2. Lock and reload the current document.
3. Determine which editable values actually changed.
4. Persist changed values without changing `content_revision`.
5. Append `document.metadata_updated` only when at least one value changed.
6. Commit both changes together.
7. A no-op update emits no event.

### File replacement

1. Validate and write the replacement under a new UUID storage name.
2. Start a transaction and lock the current document.
3. Increment `content_revision`.
4. Persist the new file reference, checksum, type, size, and metadata changes.
5. Append `document.content_replaced` with the new revision and checksum.
6. Append a metadata event only if editable metadata also changed.
7. Commit.
8. If persistence fails, remove the new file and retain the old reference.
9. After success, attempt to remove the superseded physical file without
   converting a committed update into a reported failure.

### Deletion

1. Lock and reload the current document.
2. Snapshot the bounded physical bytes for compensation.
3. Remove the physical file.
4. Insert `document.deleted` with the final revision and checksum.
5. Delete `Document` in the same database transaction.
6. Commit.
7. If database persistence fails, restore the physical file and roll back the
   deletion event.

## Outbox delivery semantics

### Claiming

The outbox adapter claims no more than the configured batch size. A claim:

- Selects pending events whose `available_at` is due.
- Reclaims claimed events whose lease expired.
- Assigns a unique `claim_token` and expiration time.
- Increments `attempt_count` when delivery begins.
- Returns immutable envelopes plus the claim token.

Delivery-state updates require both event ID and claim token. A stale worker
cannot dispatch or retry an event after its lease is replaced.

### Callback success

The dispatcher calls:

```python
callback.handle(event: DocumentEventEnvelope) -> None
```

After a successful return, it marks the event dispatched and records
`dispatched_at`. Callback implementations must be idempotent because a process
can fail after the callback succeeds but before the success marker commits.

### Callback failure

Expected callback exceptions expose a safe machine-readable error code.
Unexpected exceptions are logged without payloads or file paths and recorded as
`callback_failed`.

Failures below the attempt limit return to pending with exponential backoff:

```text
delay = min(5 seconds * 2 ** (attempt_count - 1), 15 minutes)
```

The default maximum is eight attempts. The eighth failure marks the event
`dead_letter`. Dead-letter records remain queryable and may be explicitly
requeued by a management-command option.

The delivery guarantee is at least once, never exactly once.

## Direct callback service

`DirectCallbackService` consumes:

- `OutboxPort`
- `DocumentEventCallback`
- `Clock`
- Batch size, lease duration, and maximum attempts

Its `dispatch_once()` method claims a batch, handles each event independently,
and returns:

```python
@dataclass(frozen=True)
class DispatchReport:
    claimed: int
    dispatched: int
    retried: int
    dead_lettered: int
```

One event failure does not prevent remaining claimed events from being
processed.

## Revision reconciliation service

The reconciliation layer defines:

```python
@dataclass(frozen=True)
class IndexedDocumentRevision:
    document_id: UUID
    content_revision: int
    source_sha256: str
    source_updated_at: datetime
```

It consumes separate ports:

- `DocumentRevisionRepository.list_current()`
- `RagRevisionStateReader.list_indexed()`
- `RagSyncCommandSink.request_sync(snapshot)`
- `RagSyncCommandSink.request_delete(document_id)`

Comparison rules:

- Source exists and indexed state does not: request synchronization.
- Both exist but revision, checksum, or source update timestamp differs: request
  synchronization.
- Both exist and revision, checksum, and source update timestamp match: no
  action.
- Indexed state exists but source does not: request deletion.

The service returns:

```python
@dataclass(frozen=True)
class ReconciliationReport:
    source_count: int
    indexed_count: int
    requested_sync: int
    requested_delete: int
    current: int
    failed: int
```

Per-document command failures are collected and do not stop unrelated
reconciliation work. The service never edits documents or outbox state.

## Management commands

### dispatch_document_outbox

The command loads the configured callback adapter by dotted path, constructs
the Django outbox adapter and callback service, dispatches one bounded batch,
prints the report, and returns nonzero for configuration or infrastructure
failure.

Options include:

- `--batch-size`
- `--lease-seconds`
- `--max-attempts`
- `--requeue-dead-letter EVENT_UUID`
- `--dry-run`

Dry-run reports eligible event counts without claiming or delivering them.

### reconcile_document_revisions

The command loads configured RAG state-reader and command-sink adapters,
constructs the Django revision repository and polling service, performs one
comparison pass, and prints the report.

Options include:

- `--dry-run`
- `--fail-on-item-error`

Dry-run performs comparisons and reports proposed actions without invoking the
command sink.

The commands are scheduler-neutral. Deployment documentation supplies examples
for invoking them periodically but does not install or select cron, Celery
Beat, APScheduler, or another scheduler.

## Configuration

Settings use dotted import paths:

```text
DOCUMENT_EVENT_CALLBACK
DOCUMENT_RAG_REVISION_STATE_READER
DOCUMENT_RAG_SYNC_COMMAND_SINK
DOCUMENT_OUTBOX_BATCH_SIZE, default 50
DOCUMENT_OUTBOX_LEASE_SECONDS, default 60
DOCUMENT_OUTBOX_MAX_ATTEMPTS, default 8
```

Missing downstream adapter settings do not prevent Django startup, migrations,
document CRUD, or document tests. They produce a clear management-command
configuration error only when the corresponding integration command runs.

## Error handling and observability

- Logs identify documents and events by UUID only.
- Logs never include file bytes, extracted content, physical paths, callback
  payloads, or arbitrary exception text.
- Callback failures persist a bounded safe error code.
- Lease and retry transitions are explicit and testable.
- Configuration errors name the missing setting.
- Management commands emit one structured summary per run.
- Database failures preserve transaction and file-compensation behavior.
- Reconciliation item failures are represented in the report.

## API compatibility

Existing URLs and mutation behavior remain unchanged. Serialized document
responses add:

```json
{
  "contentRevision": 1
}
```

The existing Next.js document type adds the corresponding numeric field. No
outbox, callback, polling, or RAG endpoint is exposed publicly.

## Testing strategy

### Document app

- Migration initializes existing and new documents at revision `1`.
- The router sends outbox reads, writes, and migrations to `documents`.
- Creation writes a matching event.
- Metadata changes emit one event without incrementing revision.
- No-op metadata updates emit no event.
- Replacement increments revision and emits the new checksum.
- Replacement plus metadata changes emits both event types.
- Deletion leaves its event after the document record is gone.
- Forced outbox failure rolls back each database mutation.
- File compensation still succeeds for create, replace, and delete failures.
- Public DTOs are immutable and do not expose storage paths.

### Outbox

- Due pending events are claimed.
- Future events are not claimed.
- Active leases are not stolen.
- Expired leases are reclaimed with a new token.
- Stale claim tokens cannot update state.
- Successful delivery is recorded once.
- Retry delays follow the bounded formula.
- Attempt eight dead-letters an event.
- Explicit requeue resets delivery state safely.

### Callback service

- Success dispatches an event.
- Expected and unexpected callback failures receive safe codes.
- One failure does not stop the rest of a batch.
- Reports count every outcome.
- Repeated delivery exposes the same event UUID.
- Service tests use only protocol fakes.

### Reconciliation service

- Missing source index requests are detected.
- Revision, checksum, and metadata-update mismatches request synchronization.
- Matching entries are counted current.
- Downstream-only entries request deletion.
- Per-item failures are collected.
- Dry-run proposes actions without invoking the sink.
- Service tests use only protocol fakes.

### Commands and architecture

- Commands load valid dotted-path adapters.
- Missing or invalid settings return clear nonzero errors.
- Command options override defaults.
- Dry-run does not mutate outbox or downstream state.
- `documents` contains no imports from `document_integrations` or `rag`.
- Core integration services contain no Django ORM imports.
- All document tests pass without integration adapter configuration.
- All integration tests pass without Redis, a scheduler, or a RAG app.
- Existing Django, frontend document, TypeScript, build, migration, and Compose
  checks remain green.

## Execution constraints

- Implementation is test-driven: every behavior begins with a focused failing
  test.
- Each task produces an independently reviewable, passing unit.
- No RAG implementation or provider dependency is introduced.
- No scheduler runtime is selected.
- Existing unrelated working-tree changes are preserved.

## Future integration

A future RAG app may implement either or both integration paths:

- A callback adapter for low-latency, at-least-once lifecycle processing.
- Revision-state and synchronization adapters for scheduled reconciliation.

Using both is recommended: callbacks provide prompt processing, while polling
provides eventual consistency and repairs missed or manually altered indexing
state.
