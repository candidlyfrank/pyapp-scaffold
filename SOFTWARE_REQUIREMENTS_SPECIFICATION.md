# Software Requirements Specification

## Document Library and RAG Readiness

| Document field | Value |
| --- | --- |
| System | Document Library and Future RAG Integration |
| Version | 1.0 |
| Status | Draft baseline |
| Date | 24 July 2026 |
| Frontend | Next.js application in `src/frontend` |
| Source service | Django application in `src/django` |
| Current document database | Dedicated SQLite database |
| Intended future database | PostgreSQL |

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification (SRS) defines the functional,
interface, data, security, reliability, and quality requirements for:

1. uploading and validating documents;
2. storing document files and metadata;
3. managing documents through a Next.js library;
4. publishing document lifecycle changes for downstream consumers;
5. reconciling the document source of truth with a future RAG index; and
6. extending the system into an end-to-end retrieval-augmented generation
   (RAG) application.

This SRS distinguishes implemented baseline requirements from future RAG
requirements. A future requirement is normative for planned work but is not a
claim that the capability currently exists.

### 1.2 Scope

The current system consists of:

- a Next.js upload and document-management interface;
- a Django document API;
- project-local physical file storage;
- a dedicated SQLite database for document metadata and outbox events;
- content revision and SHA-256 tracking;
- a transactional durable outbox;
- a transport-independent callback dispatch service;
- an independent revision polling and reconciliation service;
- scheduler-neutral Django management commands;
- a dedicated frontend verification job covering locked installation, type
  checking, the complete frontend test suite, and a production build; and
- production dependency audit gates for the frontend and Python service
  runtime graphs.

The current system does not extract document text, create chunks or embeddings,
store vectors, retrieve context, call a language model, or generate answers.
Those capabilities are defined as future requirements in this SRS.

### 1.3 Intended audience

This document is intended for:

- frontend and backend engineers;
- RAG and machine-learning engineers;
- software architects;
- testers and quality engineers;
- platform and operations engineers;
- security reviewers; and
- product owners responsible for document and knowledge-management workflows.

### 1.4 Requirement language

The key words **SHALL**, **SHALL NOT**, **SHOULD**, and **MAY** are normative:

- **SHALL** indicates a mandatory requirement.
- **SHALL NOT** indicates a prohibited behaviour.
- **SHOULD** indicates a recommended requirement that may be omitted only with
  a documented reason.
- **MAY** indicates an optional capability.

### 1.5 Requirement status

Requirements use the following status values:

| Status | Meaning |
| --- | --- |
| Implemented | The requirement is present in the current codebase. |
| Partial | Supporting capability exists, but additional work is required. |
| Future | The requirement is planned for the RAG system or production hardening. |

### 1.6 Definitions and abbreviations

| Term | Definition |
| --- | --- |
| CMS | Content management functionality used to manage uploaded resources. |
| Document | A logical resource containing metadata and a reference to one current physical file. |
| Content revision | A monotonic integer identifying the current version of a document's source bytes. |
| Checksum | The SHA-256 digest calculated from the source file bytes. |
| Outbox | Durable database records representing lifecycle events awaiting delivery. |
| RAG | Retrieval-augmented generation. |
| Chunk | A provenance-bearing section of extracted document content used for retrieval. |
| Indexed revision | The document revision and checksum currently represented in a RAG index. |
| Source of truth | The Django document library and its current files, metadata, and revisions. |
| Adapter | An implementation that connects a stable interface to external infrastructure or a future RAG system. |

### 1.7 Related documentation

- `docs/architecture/document-file-handling-and-rag-readiness.md`
- `docs/architecture/README.md`
- `docs/API.md`

## 2. Overall Description

### 2.1 Product perspective

The document library is an independently operable source system. Future RAG
components shall integrate downstream through stable contracts.

```text
Next.js document UI
        |
        v
Django document source of truth
        |
        v
Document integration interfaces
        |
        v
Future RAG application and infrastructure
```

The required dependency direction is:

```text
documents <- document_integrations <- future RAG adapters
```

The `documents` app owns source files, metadata, validation, revisions, and
outbox events. The `document_integrations` app owns delivery and reconciliation
orchestration. The future RAG system shall own extraction, chunking, embeddings,
index storage, retrieval, prompts, and model calls.

### 2.2 Product functions

The implemented baseline provides:

- multi-file upload with per-file progress and retry;
- validation of PDF, DOCX, TXT, Markdown, and CSV files;
- safe filename handling;
- dedicated document metadata persistence;
- file download;
- document search, filtering, and sorting;
- metadata editing, including filename modification;
- physical file replacement;
- document deletion;
- content revision and checksum tracking;
- durable lifecycle events;
- callback delivery with lease, retry, and dead-letter behaviour; and
- RAG revision reconciliation through configurable interfaces.

The planned RAG system will provide:

- revision-safe source-content access;
- format-specific extraction and normalization;
- provenance-preserving chunking;
- embedding generation;
- vector and index persistence;
- background indexing and deletion jobs;
- retrieval and optional reranking;
- grounded answer generation with citations;
- authorization-aware retrieval;
- indexing status and operational controls; and
- quality and reliability evaluation.

### 2.3 User classes

| User class | Responsibilities |
| --- | --- |
| Document manager | Uploads, searches, edits, replaces, downloads, and deletes documents. |
| RAG user | Asks questions and receives evidence-grounded answers from permitted documents. |
| Operator | Runs migrations, dispatches events, schedules reconciliation, monitors failures, and restores data. |
| RAG integrator | Implements the callback, indexed-state reader, synchronization sink, extraction, indexing, and retrieval adapters. |
| Administrator | Manages users, permissions, ownership, retention, and operational policy when authentication is added. |

### 2.4 Operating environment

The implemented system runs as part of the project's Docker Compose
environment and includes:

- Next.js for the browser interface;
- Django for the document API and document integration commands;
- Caddy as the integrated public origin and reverse proxy;
- SQLite for the dedicated document database;
- a project-local or configured filesystem storage root; and
- PostgreSQL for unrelated existing Django application data.

The future RAG runtime, worker framework, scheduler, embedding provider, vector
store, and language-model provider are intentionally unspecified.

### 2.5 Constraints

- The document library shall remain independently operable without a RAG
  service.
- The document app shall not import a future RAG package.
- The document metadata and outbox shall use the `documents` database alias.
- The current implementation shall use a separate SQLite database until a
  later PostgreSQL migration.
- The initial maximum upload size shall be 25 MB per file.
- Authentication and authorization are deferred but shall be completed before
  public production use.
- Callback delivery shall be treated as at least once.
- Scheduling shall remain external to the callback and polling services.
- The database and file store are separate resources and cannot be assumed to
  be crash-atomic.

### 2.6 Assumptions and dependencies

- Caddy routes relative browser `/api/*` requests to Django.
- The configured document data root is writable by the Django process.
- Database migrations have been applied to the `documents` database alias.
- Future callback consumers can deduplicate events by event UUID.
- Future RAG storage can report the revision state it currently indexes.
- Future RAG workers can retrieve source bytes through an explicit,
  revision-safe content interface.

### 2.7 Expected benefits

| Benefit | Supporting requirements |
| --- | --- |
| Independent document management | AR-001 through AR-005 keep uploads and CRUD operable without RAG infrastructure. |
| Reliable downstream notification | FR-EVT and FR-CBK preserve committed lifecycle changes and provide recoverable delivery. |
| Reduced indexing cost | FR-REV distinguishes metadata changes from source-byte changes so consumers can avoid unnecessary extraction and embeddings. |
| Deterministic stale-content detection | Revision, checksum, and update-time comparison in FR-REC identifies missing or outdated index state. |
| Recovery from missed events or restored data | Revision reconciliation provides an independent consistency-repair path. |
| Replaceable RAG infrastructure | RAG-IF and NFR-MNT isolate callback transport, index technology, providers, and scheduling behind focused interfaces. |
| Auditable answers | RAG-DATA, RAG-CHK, RAG-RET, and RAG-GEN require revision identity and source provenance through retrieval and citation. |
| Lower-risk database migration | AR-DB keeps the document persistence boundary separate while preserving the public API during a later PostgreSQL move. |

## 3. System Architecture Requirements

### 3.1 Separation of concerns

| ID | Status | Requirement |
| --- | --- | --- |
| AR-001 | Implemented | The `documents` app SHALL own document validation, source file references, metadata, revisions, and lifecycle events. |
| AR-002 | Implemented | The `document_integrations` app SHALL own callback dispatch and revision reconciliation orchestration. |
| AR-003 | Implemented | Integration services SHALL depend on protocols and immutable data-transfer objects rather than future RAG implementations. |
| AR-004 | Implemented | Django ORM and configuration loading SHALL remain infrastructure adapters outside the integration service core. |
| AR-005 | Implemented | The `documents` app SHALL NOT import `document_integrations` or a future RAG package. |
| AR-006 | Future | Extraction, chunking, embeddings, vector storage, retrieval, prompt construction, and model calls SHALL be owned by a separate RAG component. |
| AR-007 | Future | A change of RAG provider, vector store, or scheduler SHALL NOT require changes to document CRUD behaviour. |

### 3.2 Persistence boundaries

| ID | Status | Requirement |
| --- | --- | --- |
| AR-DB-001 | Implemented | Document models SHALL be routed to the `documents` database alias. |
| AR-DB-002 | Implemented | The `documents` alias SHALL use `src/django/.data/documents/metadata.sqlite3` by default. |
| AR-DB-003 | Implemented | `DJANGO_DOCUMENT_DATA_ROOT` SHALL be able to relocate the document SQLite database and physical file directory together. |
| AR-DB-004 | Implemented | Non-document Django applications SHALL remain outside the `documents` database. |
| AR-DB-005 | Future | Migration to PostgreSQL SHALL preserve public document API contracts and Next.js routes. |
| AR-DB-006 | Future | Migration to PostgreSQL SHALL introduce effective row-level locking for document mutations that request `select_for_update()`. |

## 4. External Interface Requirements

### 4.1 Next.js user interface

| ID | Status | Requirement |
| --- | --- | --- |
| UI-001 | Implemented | The system SHALL provide `/documents/upload` for document selection and upload. |
| UI-002 | Implemented | The upload interface SHALL support multiple selected files. |
| UI-003 | Implemented | The upload interface SHALL display per-file upload progress and outcome. |
| UI-004 | Implemented | A failed file SHALL be retryable without discarding successful uploads. |
| UI-005 | Implemented | The system SHALL provide `/documents` as a separate document library page. |
| UI-006 | Implemented | The library SHALL support search, filtering, sorting, detail navigation, and download. |
| UI-007 | Implemented | The system SHALL provide `/documents/{id}` for document detail and management. |
| UI-008 | Implemented | The detail page SHALL allow filename, title, description, and tag modification. |
| UI-009 | Implemented | The detail page SHALL allow physical file replacement and document deletion. |
| UI-010 | Implemented | The UI SHALL display data returned by Django rather than maintaining an independent document catalogue. |
| UI-011 | Future | The UI SHALL display RAG indexing state without making the source `Document` model own that state. |
| UI-012 | Future | The UI SHOULD provide authorized retry or reindex actions for failed or stale RAG documents. |

### 4.2 HTTP API

| ID | Status | Requirement |
| --- | --- | --- |
| API-001 | Implemented | `GET /api/documents/` SHALL list serialized document records. |
| API-002 | Implemented | `POST /api/documents/` SHALL accept one or more multipart files. |
| API-003 | Implemented | `GET /api/documents/{id}/` SHALL return a document record or a structured not-found error. |
| API-004 | Implemented | `PATCH /api/documents/{id}/` SHALL accept JSON metadata updates. |
| API-005 | Implemented | `PATCH /api/documents/{id}/` SHALL accept multipart metadata and an optional replacement file. |
| API-006 | Implemented | `DELETE /api/documents/{id}/` SHALL delete a document and return an empty success response. |
| API-007 | Implemented | `GET /api/documents/{id}/download/` SHALL stream the current file as an attachment. |
| API-008 | Implemented | Mutation requests SHALL use Django CSRF protection. |
| API-009 | Implemented | API errors SHALL use stable machine-readable codes and human-readable messages. |
| API-010 | Implemented | Validation errors SHOULD identify invalid fields when field-level context exists. |
| API-011 | Implemented | The serialized document SHALL include `id`, `filename`, `title`, `description`, `tags`, `contentType`, `size`, `sha256`, `contentRevision`, timestamps, and `downloadUrl`. |

### 4.3 Query interface

| ID | Status | Requirement |
| --- | --- | --- |
| API-QRY-001 | Implemented | The collection API SHALL support title and filename search through `q`. |
| API-QRY-002 | Implemented | The collection API SHALL support exact canonical content-type filtering. |
| API-QRY-003 | Implemented | The collection API SHALL support case-insensitive exact tag filtering. |
| API-QRY-004 | Implemented | The collection API SHALL support ordering by creation time, update time, or filename. |
| API-QRY-005 | Implemented | Unsupported ordering values SHALL return a structured validation error. |

### 4.4 Management command interface

| ID | Status | Requirement |
| --- | --- | --- |
| CLI-001 | Implemented | `dispatch_document_outbox` SHALL process one bounded callback batch and terminate. |
| CLI-002 | Implemented | The dispatch command SHALL support dry-run eligible-event reporting. |
| CLI-003 | Implemented | The dispatch command SHALL support dead-letter requeue by event UUID. |
| CLI-004 | Implemented | `reconcile_document_revisions` SHALL perform one source-to-index reconciliation pass and terminate. |
| CLI-005 | Implemented | The reconciliation command SHALL support dry-run operation. |
| CLI-006 | Implemented | The reconciliation command SHALL optionally fail when one or more item requests fail. |
| CLI-007 | Implemented | Missing required adapters SHALL produce an explicit configuration error. |
| CLI-008 | Future | The deployment environment SHALL schedule the one-shot commands at documented intervals. |

### 4.5 Future RAG adapter interface

| ID | Status | Requirement |
| --- | --- | --- |
| RAG-IF-001 | Partial | `DOCUMENT_EVENT_CALLBACK` SHALL resolve to an adapter implementing `handle(event)`. |
| RAG-IF-002 | Partial | `DOCUMENT_RAG_REVISION_STATE_READER` SHALL resolve to an adapter implementing `list_indexed()`. |
| RAG-IF-003 | Partial | `DOCUMENT_RAG_SYNC_COMMAND_SINK` SHALL resolve to an adapter implementing `request_sync(snapshot)` and `request_delete(document_id)`. |
| RAG-IF-004 | Future | Production implementations of all three configured adapters SHALL be supplied by the RAG or infrastructure layer. |
| RAG-IF-005 | Future | A RAG-owned source reader SHALL retrieve the current document bytes and metadata using a document UUID and expected revision or checksum. |
| RAG-IF-006 | Future | The source reader SHALL NOT rely on undocumented physical storage paths. |

### 4.6 Documentation interface

| ID | Status | Requirement |
| --- | --- | --- |
| API-DOC-001 | Implemented | `docs/API.md` SHALL document the current HTTP interfaces, CSRF flow, error format, document query and mutation contracts, and document integration commands. |

## 5. Data Requirements

### 5.1 Document entity

| Field | Requirement |
| --- | --- |
| `id` | Stable UUID primary identifier. |
| `file` | Reference to the current physical storage object. |
| `filename` | Editable, safe, user-facing download filename. |
| `title` | Required user-facing title from 1 to 255 characters. |
| `description` | Optional text up to 5,000 characters. |
| `tags` | Normalized list of no more than 20 unique tags, each no more than 50 characters. |
| `content_type` | Canonical content type assigned after server-side validation. |
| `size` | Validated file size in bytes. |
| `sha256` | SHA-256 checksum of the current source bytes. |
| `content_revision` | Positive monotonic integer starting at 1. |
| `created_at` | Source record creation timestamp. |
| `updated_at` | Most recent source record update timestamp. |

### 5.2 Physical file storage

| ID | Status | Requirement |
| --- | --- | --- |
| DATA-FILE-001 | Implemented | Physical files SHALL be stored beneath the configured document files root. |
| DATA-FILE-002 | Implemented | Physical storage names SHALL be generated independently of user-controlled filenames. |
| DATA-FILE-003 | Implemented | Editing `filename` SHALL NOT rename or relocate the physical storage object. |
| DATA-FILE-004 | Implemented | Download responses SHALL use the current editable filename as the attachment name. |
| DATA-FILE-005 | Implemented | A download request SHALL detect and report when the referenced physical file is missing. |
| DATA-FILE-006 | Future | Operations SHALL audit for orphaned files and database records whose physical file is missing. |
| DATA-FILE-007 | Future | Backup and restore procedures SHALL cover the document database and physical files as one recoverable dataset. |

### 5.3 Durable outbox entity

The outbox shall contain:

| Field | Requirement |
| --- | --- |
| Event ID | Stable UUID used as the delivery deduplication key. |
| Event type | Constrained lifecycle event name. |
| Schema version | Positive event contract version, initially 1. |
| Document ID | Plain UUID that survives source document deletion. |
| Content revision | Source revision associated with the event. |
| Source SHA-256 | Source checksum associated with the event. |
| Payload | Minimal event-specific JSON metadata with no file bytes or storage paths. |
| Occurred at | Event creation timestamp. |
| Status | `pending`, `claimed`, `dispatched`, or `dead_letter`. |
| Available at | Earliest time at which delivery may be claimed. |
| Claim token | Token authorizing the current claimant to change delivery state. |
| Claim expiry | Time after which an interrupted claim becomes eligible again. |
| Attempt count | Number of delivery claims. |
| Last error code | Bounded, safe, machine-readable failure code. |
| Dispatched at | Successful delivery timestamp. |

### 5.4 Indexed RAG state

| ID | Status | Requirement |
| --- | --- | --- |
| RAG-DATA-001 | Future | The RAG system SHALL store the indexed document UUID, content revision, source SHA-256, and source update time. |
| RAG-DATA-002 | Future | The RAG system SHALL store extraction, chunking, and embedding versions. |
| RAG-DATA-003 | Future | The RAG system SHALL store indexing status, timestamps, and the last safe error description or code. |
| RAG-DATA-004 | Future | Every chunk SHALL reference its document UUID and content revision. |
| RAG-DATA-005 | Future | Every chunk SHALL preserve available source location such as page, heading, sheet, slide, row, or section. |
| RAG-DATA-006 | Future | Index activation SHALL prevent retrieval from mixing chunks belonging to different revisions of one document. |
| RAG-DATA-007 | Future | Deleting a document SHALL remove or deactivate all chunks and vectors derived from it. |

## 6. Functional Requirements

### 6.1 Upload validation

| ID | Status | Requirement |
| --- | --- | --- |
| FR-UPL-001 | Implemented | The system SHALL accept PDF files with the `.pdf` extension when their bytes begin with the PDF signature. |
| FR-UPL-002 | Implemented | The system SHALL accept DOCX files with the `.docx` extension when they are valid ZIP packages containing `word/document.xml`. |
| FR-UPL-003 | Implemented | The system SHALL accept non-empty UTF-8 plain-text files with the `.txt` extension. |
| FR-UPL-004 | Implemented | The system SHALL accept non-empty UTF-8 Markdown files with `.md` or `.markdown` extensions. |
| FR-UPL-005 | Implemented | The system SHALL accept UTF-8 `.csv` files that parse as at least one CSV row. |
| FR-UPL-006 | Implemented | The system SHALL reject unsupported file extensions with HTTP status 415. |
| FR-UPL-007 | Implemented | The system SHALL reject files whose bytes do not match the selected supported format. |
| FR-UPL-008 | Implemented | The system SHALL reject empty files. |
| FR-UPL-009 | Implemented | The system SHALL reject a file larger than 25 MB. |
| FR-UPL-010 | Implemented | The system SHALL calculate size and SHA-256 from the uploaded bytes. |
| FR-UPL-011 | Implemented | The system SHALL assign canonical content type from server-side validation rather than trusting the browser MIME value. |
| FR-UPL-012 | Implemented | The system SHALL reduce uploaded filenames to a safe base name no longer than 255 characters. |

### 6.2 Document creation

| ID | Status | Requirement |
| --- | --- | --- |
| FR-CRE-001 | Implemented | A valid upload SHALL create a document with content revision 1. |
| FR-CRE-002 | Partial | The initial title SHALL default to the validated filename stem. The service layer MAY accept an explicit valid title; the current public multi-file upload API does not expose that option. |
| FR-CRE-003 | Implemented | The physical file SHALL be stored using a generated storage name. |
| FR-CRE-004 | Implemented | The document record and `document.created` event SHALL commit in the same `documents` database transaction. |
| FR-CRE-005 | Implemented | On a caught persistence failure, the service SHALL attempt to remove the newly written physical file. |
| FR-CRE-006 | Implemented | Each file in a multi-file upload SHALL produce an independent success or error result. |
| FR-CRE-007 | Implemented | A mixed multi-file upload SHALL preserve successful documents when another file fails. |

### 6.3 Document retrieval

| ID | Status | Requirement |
| --- | --- | --- |
| FR-RET-001 | Implemented | The system SHALL list stored document metadata without reading every physical file into the response. |
| FR-RET-002 | Implemented | The system SHALL return a structured not-found error for an unknown document UUID. |
| FR-RET-003 | Implemented | The system SHALL check that a physical file exists before beginning download. |
| FR-RET-004 | Implemented | The system SHALL stream the current file rather than serializing it into JSON. |
| FR-RET-005 | Implemented | A missing stored file SHALL produce a structured error instead of an unhandled response. |

### 6.4 Metadata management

| ID | Status | Requirement |
| --- | --- | --- |
| FR-META-001 | Implemented | The only editable metadata fields SHALL be filename, title, description, and tags. |
| FR-META-002 | Implemented | Unknown or non-editable metadata fields SHALL be rejected. |
| FR-META-003 | Implemented | Metadata validation SHALL be completed before values are persisted. |
| FR-META-004 | Implemented | A metadata-only update SHALL preserve the current file, checksum, and content revision. |
| FR-META-005 | Implemented | A changed metadata update SHALL append `document.metadata_updated` in the same database transaction. |
| FR-META-006 | Implemented | A no-op metadata update SHALL NOT create a lifecycle event. |
| FR-META-007 | Implemented | A metadata event SHALL identify changed field names without embedding document bytes. |

### 6.5 File replacement

| ID | Status | Requirement |
| --- | --- | --- |
| FR-REP-001 | Implemented | A replacement file SHALL pass the same validation as an initial upload. |
| FR-REP-002 | Implemented | A valid replacement SHALL receive a new generated physical storage name. |
| FR-REP-003 | Implemented | Replacement SHALL update content type, size, checksum, and file reference. |
| FR-REP-004 | Implemented | Replacement SHALL increment `content_revision` exactly once. |
| FR-REP-005 | Implemented | Replacement SHALL append `document.content_replaced` in the same database transaction as the record update. |
| FR-REP-006 | Implemented | A replacement request that also changes metadata SHALL append a separate metadata event. |
| FR-REP-007 | Implemented | On a caught persistence failure, the service SHALL attempt to remove the new file and retain the original record. |
| FR-REP-008 | Implemented | After successful persistence, the service SHALL attempt to remove the superseded physical file. |

### 6.6 Document deletion

| ID | Status | Requirement |
| --- | --- | --- |
| FR-DEL-001 | Implemented | Deletion SHALL append `document.deleted` and remove the document record in the same database transaction. |
| FR-DEL-002 | Implemented | The deletion event SHALL survive deletion of the source record. |
| FR-DEL-003 | Implemented | Deletion SHALL attempt to remove the physical file. |
| FR-DEL-004 | Implemented | If physical file removal completes and a subsequent caught operation fails, the service SHALL attempt to restore the file bytes. |
| FR-DEL-005 | Future | RAG synchronization SHALL delete all indexed representations of a deleted source document. |

### 6.7 Content revision semantics

| ID | Status | Requirement |
| --- | --- | --- |
| FR-REV-001 | Implemented | Existing and newly created documents SHALL have a positive content revision. |
| FR-REV-002 | Implemented | Metadata-only changes SHALL NOT increment the content revision. |
| FR-REV-003 | Implemented | A physical file replacement SHALL increment the content revision. |
| FR-REV-004 | Implemented | Revision snapshots SHALL contain document UUID, content revision, source SHA-256, content type, size, and source update time. |
| FR-REV-005 | Implemented | Revision snapshots SHALL NOT expose physical storage paths or source bytes. |
| FR-REV-006 | Future | RAG indexing SHALL reject or cancel work when the requested revision is no longer current. |

### 6.8 Lifecycle events

| ID | Status | Requirement |
| --- | --- | --- |
| FR-EVT-001 | Implemented | Event schema version 1 SHALL support `document.created`. |
| FR-EVT-002 | Implemented | Event schema version 1 SHALL support `document.content_replaced`. |
| FR-EVT-003 | Implemented | Event schema version 1 SHALL support `document.metadata_updated`. |
| FR-EVT-004 | Implemented | Event schema version 1 SHALL support `document.deleted`. |
| FR-EVT-005 | Implemented | Created and replacement event payloads SHALL include validated filename, content type, and size. |
| FR-EVT-006 | Implemented | Metadata event payloads SHALL contain changed field names. |
| FR-EVT-007 | Implemented | Deleted event payloads SHALL include the final validated filename and content type. |
| FR-EVT-008 | Implemented | Event payloads SHALL NOT contain physical storage paths or document bytes. |
| FR-EVT-009 | Implemented | Unsupported event schema versions SHALL be rejected by callback dispatch with a safe error code. |

### 6.9 Callback dispatch

| ID | Status | Requirement |
| --- | --- | --- |
| FR-CBK-001 | Implemented | Callback dispatch SHALL claim no more than its configured batch size. |
| FR-CBK-002 | Implemented | A claim SHALL use a unique token and an expiry time. |
| FR-CBK-003 | Implemented | An expired claim SHALL become eligible for recovery. |
| FR-CBK-004 | Implemented | Only the active claim token SHALL be able to mark an event dispatched or failed. |
| FR-CBK-005 | Implemented | Successful callback handling SHALL mark the event dispatched. |
| FR-CBK-006 | Implemented | Failed callback handling SHALL store a safe machine-readable error code. |
| FR-CBK-007 | Implemented | Retryable failures SHALL use bounded exponential backoff. |
| FR-CBK-008 | Implemented | An event reaching the maximum attempt count SHALL enter dead-letter status. |
| FR-CBK-009 | Implemented | A dead-letter event SHALL be manually requeueable. |
| FR-CBK-010 | Future | Callback consumers SHALL deduplicate processing by event UUID. |

### 6.10 Revision reconciliation

| ID | Status | Requirement |
| --- | --- | --- |
| FR-REC-001 | Implemented | Reconciliation SHALL compare source documents with indexed RAG revision state. |
| FR-REC-002 | Implemented | A source document missing from RAG state SHALL request synchronization. |
| FR-REC-003 | Implemented | A differing revision, checksum, or source update time SHALL request synchronization. |
| FR-REC-004 | Implemented | Matching source and indexed state SHALL require no synchronization. |
| FR-REC-005 | Implemented | An indexed document missing from the source library SHALL request deletion. |
| FR-REC-006 | Implemented | Failure to request one item SHALL be recorded without preventing comparison of remaining items. |
| FR-REC-007 | Implemented | Dry-run reconciliation SHALL report required actions without sending sync or delete commands. |

## 7. Non-Functional Requirements

### 7.1 Reliability and consistency

| ID | Status | Requirement |
| --- | --- | --- |
| NFR-REL-001 | Implemented | A document mutation and its lifecycle event SHALL commit or roll back together within the `documents` database. |
| NFR-REL-002 | Implemented | File operations SHALL use best-effort compensation for caught database or storage failures. |
| NFR-REL-003 | Future | Operations SHALL detect file/database divergence caused by an abrupt process or storage failure. |
| NFR-REL-004 | Future | RAG synchronization SHALL be idempotent by event UUID and document revision. |
| NFR-REL-005 | Future | RAG index replacement SHALL not expose a partially indexed revision to retrieval. |
| NFR-REL-006 | Future | Backup restoration SHALL be followed by revision reconciliation. |

### 7.2 Security and privacy

| ID | Status | Requirement |
| --- | --- | --- |
| NFR-SEC-001 | Implemented | Filenames SHALL be sanitized to prevent user-controlled storage paths. |
| NFR-SEC-002 | Implemented | Supported file types SHALL be validated using file bytes. |
| NFR-SEC-003 | Implemented | Browser mutations SHALL require a valid CSRF token. |
| NFR-SEC-004 | Future | Authentication SHALL be required before the document library is publicly exposed. |
| NFR-SEC-005 | Future | The system SHALL enforce document ownership, role, sharing, and deletion permissions. |
| NFR-SEC-006 | Future | Retrieval SHALL apply the same authorization boundary as document access. |
| NFR-SEC-007 | Future | The upload pipeline SHALL include malware scanning and resource-abuse controls. |
| NFR-SEC-008 | Future | The system SHALL define retention, deletion, audit, and sensitive-data policies. |
| NFR-SEC-009 | Future | Provider logs and prompts SHALL NOT disclose document content beyond configured policy. |
| NFR-SEC-010 | Implemented | CI SHALL audit the installed frontend production dependency graph and fail when npm reports a high- or critical-severity advisory. |
| NFR-SEC-011 | Implemented | CI SHALL audit the installed Python service production dependency graphs and fail when `pip-audit` reports a known vulnerability. |

### 7.3 Performance and scalability

| ID | Status | Requirement |
| --- | --- | --- |
| NFR-PERF-001 | Implemented | Upload progress SHALL be observable per file in the frontend. |
| NFR-PERF-002 | Implemented | Callback dispatch SHALL use bounded batches. |
| NFR-PERF-003 | Future | Extraction and embedding work SHALL execute outside latency-sensitive upload requests. |
| NFR-PERF-004 | Future | RAG workers SHALL support configured concurrency and provider rate limits. |
| NFR-PERF-005 | Future | Retrieval SHALL enforce candidate and context-size limits. |
| NFR-PERF-006 | Future | Database and vector-store indexes SHALL support expected query and reconciliation workloads. |

### 7.4 Maintainability and extensibility

| ID | Status | Requirement |
| --- | --- | --- |
| NFR-MNT-001 | Implemented | Core integration services SHALL be testable with protocol-compatible fakes. |
| NFR-MNT-002 | Implemented | Callback transport and indexed-state technology SHALL be supplied as replaceable adapters. |
| NFR-MNT-003 | Implemented | Management commands SHALL remain scheduler-neutral. |
| NFR-MNT-004 | Future | Extractors, chunkers, embedding providers, vector stores, rerankers, and language models SHALL be replaceable behind focused interfaces. |
| NFR-MNT-005 | Future | Stored extraction, chunking, and embedding versions SHALL support controlled reindexing after algorithm changes. |
| NFR-MNT-006 | Implemented | Current HTTP and document integration command interfaces SHALL be maintained in `docs/API.md`. |

### 7.5 Observability

| ID | Status | Requirement |
| --- | --- | --- |
| NFR-OBS-001 | Implemented | Callback dispatch SHALL report claimed, dispatched, retried, and dead-lettered counts. |
| NFR-OBS-002 | Implemented | Reconciliation SHALL report source, indexed, sync, delete, current, and failure counts. |
| NFR-OBS-003 | Future | The system SHALL expose indexing lifecycle metrics and structured logs. |
| NFR-OBS-004 | Future | Operators SHALL be alerted to dead-letter events and sustained indexing failures. |
| NFR-OBS-005 | Future | The system SHALL provide traceability from an answer to retrieval results, chunks, document revision, and indexing job. |

### 7.6 Portability

| ID | Status | Requirement |
| --- | --- | --- |
| NFR-PORT-001 | Implemented | The document storage root SHALL be environment-configurable. |
| NFR-PORT-002 | Implemented | One-shot commands SHALL be invocable by different scheduling platforms. |
| NFR-PORT-003 | Future | Moving document metadata from SQLite to PostgreSQL SHALL not change the frontend contract. |
| NFR-PORT-004 | Future | RAG provider choices SHALL be isolated from document file-management behaviour. |

## 8. Future End-to-End RAG Requirements

### 8.1 Source access

| ID | Status | Requirement |
| --- | --- | --- |
| RAG-SRC-001 | Future | The RAG system SHALL retrieve current source bytes and required metadata through an explicit source-content interface. |
| RAG-SRC-002 | Future | The RAG system SHALL verify the requested content revision and SHA-256 before activating indexed output. |
| RAG-SRC-003 | Future | A stale indexing job SHALL NOT replace index state for a newer revision. |

### 8.2 Extraction and normalization

| ID | Status | Requirement |
| --- | --- | --- |
| RAG-EXT-001 | Future | The system SHALL extract text and available structure from PDF files. |
| RAG-EXT-002 | Future | The system SHALL extract paragraphs, headings, tables, and relevant structure from DOCX files. |
| RAG-EXT-003 | Future | The system SHALL decode and normalize TXT and Markdown files. |
| RAG-EXT-004 | Future | The system SHALL preserve row and column context when extracting CSV files. |
| RAG-EXT-005 | Future | Extractors SHALL return a common normalized representation with source locations. |
| RAG-EXT-006 | Future | Scanned PDFs and future image formats SHALL use OCR when no suitable embedded text exists. |
| RAG-EXT-007 | Future | Extractor failures SHALL produce safe, actionable indexing status without corrupting the active index. |

### 8.3 Phase-two file formats

| ID | Status | Requirement |
| --- | --- | --- |
| RAG-FMT-001 | Future | Image, spreadsheet, and PowerPoint support SHALL extend the Django upload allowlist and byte-level validation. |
| RAG-FMT-002 | Future | Phase-two formats SHALL receive canonical server-assigned content types. |
| RAG-FMT-003 | Future | The frontend file selector SHALL be updated only after backend validation supports each new format. |
| RAG-FMT-004 | Future | Spreadsheet extraction SHALL preserve workbook, sheet, table, row, and column context where available. |
| RAG-FMT-005 | Future | PowerPoint extraction SHALL preserve slide, title, note, and object context where available. |
| RAG-FMT-006 | Future | Image extraction SHALL preserve image provenance and OCR regions where available. |
| RAG-FMT-007 | Future | Every added format SHALL include validation, API, extraction, and UI tests. |

### 8.4 Chunking and provenance

| ID | Status | Requirement |
| --- | --- | --- |
| RAG-CHK-001 | Future | The system SHALL divide normalized content into retrievable chunks. |
| RAG-CHK-002 | Future | Chunking SHOULD respect structural boundaries before applying size limits. |
| RAG-CHK-003 | Future | Every chunk SHALL have a stable identifier within its document revision. |
| RAG-CHK-004 | Future | Every chunk SHALL retain available page, heading, row, sheet, slide, or section provenance. |
| RAG-CHK-005 | Future | The system SHALL record the chunking strategy version. |

### 8.5 Embeddings and indexing

| ID | Status | Requirement |
| --- | --- | --- |
| RAG-EMB-001 | Future | The system SHALL generate embeddings through a replaceable embedding adapter. |
| RAG-EMB-002 | Future | Embedding generation SHALL support batching, retry, and rate-limit handling. |
| RAG-EMB-003 | Future | The system SHALL record the embedding model and version used for each active index version. |
| RAG-EMB-004 | Future | A change to source revision, extraction version, chunking version, or embedding version SHALL make affected index content eligible for reprocessing. |
| RAG-IDX-001 | Future | The RAG system SHALL persist chunks, embeddings, metadata, and indexed revision state. |
| RAG-IDX-002 | Future | Indexing SHALL be idempotent for a document UUID and content revision. |
| RAG-IDX-003 | Future | Index activation SHALL be atomic from the retrieval consumer's perspective. |

### 8.6 Background workflow

| ID | Status | Requirement |
| --- | --- | --- |
| RAG-JOB-001 | Future | Extraction and indexing SHALL execute through a background job mechanism. |
| RAG-JOB-002 | Future | Jobs SHALL be retryable and safe to resume after worker interruption. |
| RAG-JOB-003 | Future | Jobs SHALL detect and stop processing stale document revisions. |
| RAG-JOB-004 | Future | The deployment SHALL schedule frequent bounded outbox dispatch. |
| RAG-JOB-005 | Future | The deployment SHALL schedule periodic revision reconciliation. |
| RAG-JOB-006 | Future | The deployment SHALL monitor dead-letter and failed-index states. |

### 8.7 Retrieval

| ID | Status | Requirement |
| --- | --- | --- |
| RAG-RET-001 | Future | The system SHALL normalize a user's query before retrieval. |
| RAG-RET-002 | Future | The system SHALL generate query embeddings using a compatible model. |
| RAG-RET-003 | Future | Retrieval SHALL apply authorization and metadata filters before returning context. |
| RAG-RET-004 | Future | Retrieval SHALL support vector search and MAY support keyword or hybrid search. |
| RAG-RET-005 | Future | The system MAY rerank candidate chunks through a replaceable reranking adapter. |
| RAG-RET-006 | Future | Retrieval SHALL enforce context-size, score, and diversity limits. |
| RAG-RET-007 | Future | Retrieval results SHALL include chunk content, document identity, revision, and source provenance. |

### 8.8 Generation and citations

| ID | Status | Requirement |
| --- | --- | --- |
| RAG-GEN-001 | Future | The system SHALL construct a grounded prompt from authorized retrieved chunks. |
| RAG-GEN-002 | Future | The generation layer SHALL instruct the model to distinguish evidence from unsupported information. |
| RAG-GEN-003 | Future | Generated answers SHALL cite the supporting document and source location when available. |
| RAG-GEN-004 | Future | The system SHALL report insufficient evidence when retrieval does not support an answer. |
| RAG-GEN-005 | Future | The language-model provider SHALL be replaceable without changing document management. |

### 8.9 Indexing status

| ID | Status | Requirement |
| --- | --- | --- |
| RAG-STA-001 | Future | The RAG system SHALL distinguish queued, extracting, embedding, indexed, stale, and failed states. |
| RAG-STA-002 | Future | Indexing status SHALL identify the document UUID and target content revision. |
| RAG-STA-003 | Future | A failed state SHALL retain a safe error code and retry eligibility. |
| RAG-STA-004 | Future | The frontend SHOULD display the current RAG status and indexed revision. |

### 8.10 Evaluation

| ID | Status | Requirement |
| --- | --- | --- |
| RAG-EVAL-001 | Future | The project SHALL maintain representative retrieval and grounded-answer evaluation cases. |
| RAG-EVAL-002 | Future | Evaluation SHALL measure retrieval relevance, citation correctness, and unsupported-answer rate. |
| RAG-EVAL-003 | Future | Model, chunking, extraction, and ranking changes SHALL be evaluated before production rollout. |
| RAG-EVAL-004 | Future | Authorization tests SHALL verify that retrieval cannot leak inaccessible documents. |

## 9. Current Exclusions and Limitations

The following are not part of the implemented baseline:

- a Django `rag` application or separate RAG service;
- extraction or OCR;
- normalized document representations;
- chunk storage;
- embedding generation;
- a vector database or `pgvector`;
- keyword, vector, or hybrid retrieval;
- reranking;
- prompt construction;
- language-model calls;
- grounded answers or citations;
- a production callback transport;
- production implementations of RAG polling interfaces;
- a worker, queue, or scheduler;
- authentication, ownership, or authorization;
- RAG indexing status in the Next.js UI;
- malware scanning, quotas, or retention enforcement; and
- image, spreadsheet, or PowerPoint upload acceptance.

The current SQLite database does not provide row-level `SELECT FOR UPDATE`
locking. The code requests `select_for_update()` within mutation transactions,
but effective row-level locking requires migration to a supporting database
such as PostgreSQL.

The database and file store do not share one transaction. The current services
perform best-effort compensation for caught failures, but an abrupt process or
storage failure can leave an orphaned file or a document record whose physical
file is missing.

## 10. Verification and Acceptance Criteria

### 10.1 Implemented baseline acceptance

The implemented baseline is acceptable when:

1. migrations apply successfully to the dedicated `documents` database;
2. valid PDF, DOCX, TXT, Markdown, and CSV fixtures upload successfully;
3. empty, oversized, unsupported, and content-mismatched files are rejected
   with structured errors;
4. uploaded files appear in the Next.js document library using Django data;
5. search, content-type filtering, tag filtering, and supported sorting return
   the expected records;
6. metadata and filename edits persist without incrementing content revision;
7. replacement increments content revision and recalculates the checksum from
   the replacement bytes;
8. download streams the current file using the editable filename;
9. delete removes the source record and leaves a durable deletion event;
10. every actual document lifecycle change creates the correct outbox event;
11. callback dispatch claims, dispatches, retries, dead-letters, and requeues
    events according to configuration;
12. revision reconciliation detects missing, stale, current, and deleted index
    state;
13. document services and integration services pass their isolated tests;
14. architecture tests confirm the intended dependency direction;
15. the frontend verification job completes a locked install, type check,
    complete frontend test run, and production build; and
16. the installed frontend production dependency graph passes the configured
    high-severity npm audit gate; and
17. the installed Django, FastAPI, and root Python dependency graphs pass the
    configured `pip-audit` gates.

### 10.2 End-to-end RAG acceptance

The future RAG system is acceptable when:

1. a supported uploaded document progresses to an indexed state without
   blocking the upload response;
2. the active index records the exact source document revision and checksum;
3. metadata-only changes update searchable metadata without unnecessary
   source re-embedding;
4. a replacement produces a new complete index version and retires the old
   revision atomically;
5. deletion removes the document from retrieval;
6. duplicate callbacks and repeated reconciliation are idempotent;
7. a missed callback is repaired by reconciliation;
8. stale jobs cannot replace newer index state;
9. retrieval returns authorized, relevant chunks with provenance;
10. generated answers contain verifiable citations or report insufficient
    evidence;
11. inaccessible documents cannot influence retrieval or generation;
12. provider, worker, and storage failures produce observable retry or failed
    states; and
13. the agreed evaluation suite meets documented quality thresholds.

## 11. Test Requirements

| ID | Status | Requirement |
| --- | --- | --- |
| TEST-001 | Implemented | Unit tests SHALL cover filename, tag, type, size, byte-content, and metadata validation. |
| TEST-002 | Implemented | Service tests SHALL cover creation, metadata update, replacement, deletion, event creation, and compensation paths. |
| TEST-003 | Implemented | API tests SHALL cover CRUD, download, queries, partial upload results, CSRF, and structured errors. |
| TEST-004 | Implemented | Outbox tests SHALL cover claim tokens, lease expiry, retry backoff, guarded transitions, dead-letter, and requeue behaviour. |
| TEST-005 | Implemented | Callback and polling service tests SHALL use protocol-compatible fakes without requiring a RAG provider. |
| TEST-006 | Implemented | Frontend document tests SHALL cover upload progress, retry, library data, metadata editing, replacement, and deletion. |
| TEST-007 | Implemented | Architecture tests SHALL guard separation between document and future RAG responsibilities. |
| TEST-008 | Future | Extractor fixture tests SHALL cover every supported file format and malformed input. |
| TEST-009 | Future | Chunking tests SHALL verify stable provenance and boundary behaviour. |
| TEST-010 | Future | Indexing tests SHALL cover idempotency, stale jobs, atomic revision replacement, and deletion. |
| TEST-011 | Future | End-to-end tests SHALL cover upload through grounded answer and citation. |
| TEST-012 | Future | Security tests SHALL cover authorization leakage, malicious files, and provider data handling. |
| TEST-013 | Future | Evaluation tests SHALL detect retrieval or grounded-answer regressions. |
| TEST-014 | Implemented | A dedicated frontend verification job SHALL run `npm ci`, TypeScript checking, the complete Vitest suite, and a production Next.js build. |
| TEST-015 | Implemented | Backend CI SHALL run `pip-audit` against the installed Django, FastAPI, and root Python dependency graphs. |

## 12. Operational Requirements

| ID | Status | Requirement |
| --- | --- | --- |
| OPS-001 | Partial | Deployment procedures SHALL apply document migrations before document APIs or integration commands are used. |
| OPS-002 | Implemented | The configured document data root SHALL be initialized with write permissions for the Django process. |
| OPS-003 | Future | Production deployment SHALL rebuild and recreate Django containers when document schema or command code changes. |
| OPS-004 | Future | Operators SHALL schedule callback dispatch and revision reconciliation. |
| OPS-005 | Future | Operators SHALL monitor dead-letter events, failed indexing, queue age, and reconciliation drift. |
| OPS-006 | Future | Backup and restore procedures SHALL preserve database/file consistency or document the reconciliation needed afterward. |
| OPS-007 | Implemented | Operators SHALL be able to requeue a document outbox dead-letter event. |
| OPS-008 | Future | Retention and deletion operations SHALL propagate to source storage, RAG indexes, caches, and backups according to policy. |
| OPS-009 | Future | Authorized operators SHALL be able to request document reindexing safely. |

## 13. Requirements Traceability

| Objective | Primary requirement groups | Verification |
| --- | --- | --- |
| Safe document upload | FR-UPL, FR-CRE, NFR-SEC | Validation, service, API, and frontend tests |
| Document library CRUD | UI, API, FR-RET, FR-META, FR-REP, FR-DEL | API and frontend component tests |
| Editable filenames | UI-008, DATA-FILE-003, DATA-FILE-004, FR-META | Metadata update and download tests |
| Dedicated SQLite persistence | AR-DB, DATA-FILE | Database routing and migration tests |
| Exact source identity | FR-REV, RAG-DATA | Revision and service tests |
| Durable change notification | FR-EVT, FR-CBK, NFR-REL | Outbox and callback tests |
| RAG drift repair | FR-REC, CLI-004 through CLI-006 | Polling service and command tests |
| SOLID separation | AR, NFR-MNT | Architecture and isolated unit tests |
| Implemented API discoverability | API-DOC-001, NFR-MNT-006 | Repository documentation contract and `docs/API.md` review |
| Frontend delivery quality | TEST-006, TEST-014 | Dedicated frontend verification job |
| Production dependency security | NFR-SEC-010, NFR-SEC-011, TEST-015 | Locked installs and production dependency audit gates |
| End-to-end RAG indexing | RAG-SRC, RAG-EXT, RAG-CHK, RAG-EMB, RAG-IDX, RAG-JOB | Future extractor, worker, index, and end-to-end tests |
| Grounded document answers | RAG-RET, RAG-GEN, RAG-EVAL | Future relevance, citation, and groundedness evaluations |
| Secure production operation | NFR-SEC, NFR-OBS, OPS | Future security, operational, and recovery tests |

## 14. Recommended Delivery Sequence

The remaining RAG requirements should be delivered in this order:

1. create a separate RAG package or service and indexed-revision model;
2. implement revision-safe document content and metadata access;
3. add PDF, DOCX, TXT, Markdown, and CSV extraction;
4. add provenance-preserving chunking;
5. add an embedding adapter and vector/index store;
6. implement idempotent synchronization and deletion jobs;
7. implement the callback and polling adapters;
8. add background workers and schedules;
9. implement authorization-aware retrieval;
10. add grounded generation with citations;
11. expose indexing state and operator actions in Next.js;
12. add evaluation, observability, backup/recovery, and production security;
13. extend upload, validation, extraction, and tests for images, spreadsheets,
    and PowerPoint files; and
14. migrate document metadata and outbox persistence to PostgreSQL when the
    project's operational requirements justify the change.

## 15. Approval

This SRS establishes the current document-library baseline and the planned
requirements for a separate, document-driven RAG system. Changes to requirement
scope, status, interfaces, or acceptance criteria should update this document
and retain stable requirement identifiers wherever practical.
