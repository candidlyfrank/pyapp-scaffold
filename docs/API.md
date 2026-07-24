# API Reference

This document describes the interfaces implemented by the current scaffold.
It does not describe the future extraction, embedding, vector-search, or
generation interfaces in the software requirements specification.

## Service Routing

In the Docker Compose development environment, services are available directly:

| Service | Direct base URL |
| --- | --- |
| Next.js | `http://localhost:3000` |
| Django | `http://localhost:8090` |
| FastAPI | `http://localhost:8099` |

Caddy is the public entry point in every Compose environment:

| Public path | Destination |
| --- | --- |
| `/api/*`, `/admin/*`, `/static/*`, `/media/*` | Django, with the path preserved |
| `/fastapi/*` | FastAPI, with `/fastapi` removed |
| `/health` | Caddy's own plain-text health response |
| Every other path | Next.js |

Examples in the Django and document sections use Django's direct development
origin, `http://localhost:8090`; the same paths are available through the
configured Caddy host. FastAPI examples show both their direct path and public
`/fastapi` equivalent.

The Next.js `GET /api/health` route is a service-direct container health check.
At the public Caddy origin, `/api/health` is routed to Django and is not a
frontend health endpoint.

## Authentication and CSRF

The current document API has no authentication, ownership, or authorization
checks. It is intended for local development and must not be exposed publicly
until those controls are implemented.

Django's standard CSRF middleware protects every browser mutation. To mutate a
document:

1. send `GET /api/documents/` or `GET /api/session/` with credentials enabled;
2. read the `csrftoken` cookie set by Django; and
3. send the cookie value in the `X-CSRFToken` header on `POST`, `PATCH`, or
   `DELETE`.

For example:

```bash
curl --cookie-jar cookies.txt http://localhost:8090/api/documents/
token="$(awk '$6 == "csrftoken" { print $7 }' cookies.txt)"
curl --cookie cookies.txt \
  -H "X-CSRFToken: ${token}" \
  -H "Content-Type: application/json" \
  --request PATCH \
  --data '{"title":"Updated title"}' \
  http://localhost:8090/api/documents/00000000-0000-0000-0000-000000000000/
```

A failed API CSRF check returns:

```json
{
  "error": {
    "code": "csrf_failed",
    "message": "CSRF verification failed. Refresh the page and try again."
  }
}
```

with HTTP `403 Forbidden`.

## Error Format

Django API errors use a stable envelope:

```json
{
  "error": {
    "code": "invalid_metadata",
    "message": "Document metadata is invalid.",
    "fields": {
      "title": "Enter a title from 1 to 255 characters."
    }
  }
}
```

`fields` is omitted when field-level context is unavailable. Document endpoints
can return these codes:

| Code | Typical status | Meaning |
| --- | --- | --- |
| `csrf_failed` | 403 | The CSRF cookie/header pair is absent or invalid. |
| `method_not_allowed` | 405 | The resource does not support the HTTP method. |
| `missing_files` | 400 | An upload request contains no `files` parts. |
| `invalid_filename` | 400 | A filename is empty, unsafe, or longer than 255 characters. |
| `empty_file` | 400 | A file contains no bytes. |
| `file_too_large` | 413 | A file exceeds 25 MiB. |
| `unsupported_file_type` | 415 | The filename extension is unsupported. |
| `invalid_file_content` | 415 | File bytes do not match the supported extension. |
| `malformed_json` | 400 | A JSON request body cannot be decoded. |
| `malformed_request` | 400 | Multipart `metadata` is not valid JSON. |
| `invalid_metadata` | 400 | Metadata has unknown fields or invalid values. |
| `unsupported_media_type` | 415 | A patch is neither JSON nor multipart data. |
| `document_not_found` | 404 | The document UUID does not exist. |
| `stored_file_missing` | 404 | Metadata exists but the physical file is unavailable. |
| `document_persistence_failed` | 500 | Database or filesystem persistence failed. |

The Next.js interactions handler uses the simpler shape
`{"error":"message"}` for its `400` and `415` responses.

## Django API

### Browser and health routes

| Interface | Response |
| --- | --- |
| `GET /` | Django scaffold HTML page. |
| `GET /health/` | Django service status JSON. |
| `GET /playground/` | Django scaffold HTML page. |
| `GET /playground/hello/` | Example rendered template. |
| `/admin/` | Django admin interface. |

`GET /health/` returns:

```json
{
  "service": "django",
  "status": "ok",
  "port": 8090
}
```

### `GET /api/session/`

Returns the current Django session state and ensures a CSRF cookie is present:

```json
{
  "authenticated": false,
  "username": null
}
```

For an authenticated Django user, `authenticated` is `true` and `username`
contains the account's username. Document authorization is not implemented.

### `POST /api/example-mutation/`

A CSRF-protected example mutation. A valid request returns:

```json
{
  "status": "saved"
}
```

with HTTP `200 OK`. Other methods return `405 Method Not Allowed`.

### `POST /api/chat`

Provides the scaffold's asynchronous mock Django chat response. It accepts
`application/json`:

```json
{
  "content": "Explain the deployment topology."
}
```

`content` is trimmed and must contain between 1 and 500 characters. A successful
response is delayed by approximately one to two seconds and returns:

```json
{
  "id": "93b4b8f4-685a-45a6-a7c6-dde4d2c2587d",
  "content": "Thanks for your message: Explain the deployment topology.",
  "sender": "assistant",
  "timestamp": "2026-07-24T01:00:00+00:00"
}
```

Invalid media type returns `415` with `unsupported_media_type`; malformed JSON
returns `400` with `malformed_json`; invalid content returns `400` with
`invalid_content`.

## Document API

Supported upload formats are PDF (`.pdf`), DOCX (`.docx`), UTF-8 text (`.txt`),
UTF-8 Markdown (`.md` or `.markdown`), and UTF-8 CSV (`.csv`). Django validates
the file bytes rather than trusting the browser-provided MIME type. Each file is
limited to 25 MiB.

### Document representation

Document JSON uses this shape:

```json
{
  "id": "4c764354-7969-4308-a647-0c1224780ba0",
  "filename": "project-brief.pdf",
  "title": "project-brief",
  "description": "",
  "tags": ["planning", "reference"],
  "contentType": "application/pdf",
  "size": 18423,
  "sha256": "9dcac73f5e83d3e47121b69c63242c48feb713d4ca36d7c4ab5a80fd48847c0b",
  "contentRevision": 1,
  "createdAt": "2026-07-24T01:00:00+00:00",
  "updatedAt": "2026-07-24T01:00:00+00:00",
  "downloadUrl": "/api/documents/4c764354-7969-4308-a647-0c1224780ba0/download/"
}
```

The initial title is the validated filename stem. The public multi-file upload
endpoint does not accept initial metadata; metadata can be changed afterward.

### `GET /api/documents/`

Returns:

```json
{
  "documents": []
}
```

Supported query parameters:

| Parameter | Meaning |
| --- | --- |
| `q` | Case-insensitive substring search over title and filename. |
| `content_type` | Exact canonical content-type match. |
| `tag` | Case-insensitive exact tag match. |
| `ordering` | Sort order; defaults to `-created_at`. |

Supported `ordering` values are `created_at`, `-created_at`, `updated_at`,
`-updated_at`, `filename`, and `-filename`. Any other value returns `400` with
`invalid_query`.

This endpoint also sets the CSRF cookie used by document mutations.

### `POST /api/documents/`

Accepts `multipart/form-data` with one or more fields named `files`:

```bash
curl --cookie cookies.txt \
  -H "X-CSRFToken: ${token}" \
  --form "files=@brief.pdf" \
  --form "files=@notes.md" \
  http://localhost:8090/api/documents/
```

When every file succeeds, the endpoint returns HTTP `201 Created`:

```json
{
  "results": [
    {
      "filename": "brief.pdf",
      "status": "uploaded",
      "document": {
        "id": "4c764354-7969-4308-a647-0c1224780ba0",
        "filename": "brief.pdf",
        "title": "brief",
        "description": "",
        "tags": [],
        "contentType": "application/pdf",
        "size": 18423,
        "sha256": "9dcac73f5e83d3e47121b69c63242c48feb713d4ca36d7c4ab5a80fd48847c0b",
        "contentRevision": 1,
        "createdAt": "2026-07-24T01:00:00+00:00",
        "updatedAt": "2026-07-24T01:00:00+00:00",
        "downloadUrl": "/api/documents/4c764354-7969-4308-a647-0c1224780ba0/download/"
      }
    }
  ]
}
```

When some files succeed and others fail, successful documents are retained and
the endpoint returns HTTP `207 Multi-Status`. Each failed item has
`"status":"error"` and its own structured `error`. A single failed single-file
request returns that error directly with its normal `400`, `413`, `415`, or
`500` status.

### `GET /api/documents/{id}/`

Returns one document representation with HTTP `200 OK`, or
`document_not_found` with HTTP `404 Not Found`.

### `PATCH /api/documents/{id}/`

For a metadata-only update, send `application/json`:

```bash
curl --cookie cookies.txt \
  -H "X-CSRFToken: ${token}" \
  -H "Content-Type: application/json" \
  --request PATCH \
  --data '{
    "filename": "launch-plan.pdf",
    "title": "Launch plan",
    "description": "Approved launch plan",
    "tags": ["approved", "launch"]
  }' \
  http://localhost:8090/api/documents/4c764354-7969-4308-a647-0c1224780ba0/
```

Every field is optional. Supported fields and limits are:

| Field | Constraint |
| --- | --- |
| `filename` | Safe non-empty base name, at most 255 characters. |
| `title` | Non-empty after trimming, at most 255 characters. |
| `description` | String of at most 5,000 characters. |
| `tags` | Array of at most 20 strings; each tag is at most 50 characters. |

Tags are trimmed, deduplicated case-insensitively, and sorted
case-insensitively. Metadata-only updates do not increment `contentRevision`.

To replace the physical file, send `multipart/form-data`. The `metadata` field
must contain a JSON object and `file` contains the replacement:

```bash
curl --cookie cookies.txt \
  -H "X-CSRFToken: ${token}" \
  --request PATCH \
  --form 'metadata={"title":"Revised launch plan"};type=application/json' \
  --form "file=@launch-plan-v2.pdf" \
  http://localhost:8090/api/documents/4c764354-7969-4308-a647-0c1224780ba0/
```

A replacement is validated like an upload, recalculates size, canonical content
type and SHA-256, and increments `contentRevision`. A request can update metadata
and replace the file together. A successful patch returns the updated document.

### `DELETE /api/documents/{id}/`

Deletes the document and current physical file and writes a durable deletion
event. Success returns HTTP `204 No Content`.

### `GET /api/documents/{id}/download/`

Streams the current file as an attachment. The editable `filename` is used in
`Content-Disposition`, while the canonical `contentType` is used for
`Content-Type`.

## FastAPI

FastAPI is directly available on port `8099` in development and publicly below
`/fastapi` through Caddy.

| Direct interface | Public interface | Response |
| --- | --- | --- |
| `GET /` | `GET /fastapi/` | Service metadata plus documentation links. |
| `GET /health` | `GET /fastapi/health` | Liveness metadata. |
| `GET /ready` | `GET /fastapi/ready` | `ready` during application lifespan, otherwise `starting`. |
| `GET /docs` | `GET /fastapi/docs` | Swagger UI. |
| `GET /redoc` | `GET /fastapi/redoc` | ReDoc UI. |
| `GET /openapi.json` | `GET /fastapi/openapi.json` | OpenAPI schema. |
| `GET /favicon.ico` | `GET /fastapi/favicon.ico` | Empty `204` response. |

`GET /` returns:

```json
{
  "service": "fastapi",
  "status": "ok",
  "port": 8099,
  "docs": "/docs",
  "health": "/health",
  "ready": "/ready"
}
```

`GET /health` returns:

```json
{
  "service": "fastapi",
  "status": "ok",
  "port": 8099
}
```

`GET /ready` normally returns:

```json
{
  "service": "fastapi",
  "status": "ready",
  "port": 8099
}
```

## Next.js Route Handlers

### `GET /api/health`

This service-direct endpoint is used by the frontend container health check:

```json
{
  "service": "frontend",
  "status": "ok"
}
```

Use `http://localhost:3000/api/health` in development. As described under
service routing, the public Caddy `/api/*` rule sends that path to Django.

### `POST /chat/api/chat`

This is the implemented Next.js mock interactions handler. It accepts
`application/json`:

```json
{
  "message": "Build an API rollout plan",
  "model": "K2.6",
  "mode": "Standard"
}
```

`message` is trimmed and must contain between 1 and 4,000 characters. Supported
models are `K2.6` and `Gemini 2.5 Pro`; supported modes are `Standard` and
`Thinking`.

A successful response returns:

```json
{
  "id": "93b4b8f4-685a-45a6-a7c6-dde4d2c2587d",
  "content": "## A practical plan\n\n1. Clarify the outcome...",
  "createdAt": "2026-07-24T01:00:00.000Z"
}
```

Unsupported media type returns HTTP `415`; malformed or invalid request content
returns HTTP `400`.

## Document Integration Commands

These are bounded, one-shot Django management commands. The repository does not
include a scheduler; production scheduling remains an operational responsibility.

### `dispatch_document_outbox`

Dispatches one eligible batch through the configured
`DOCUMENT_EVENT_CALLBACK` adapter:

```bash
cd src/django
uv run python manage.py dispatch_document_outbox \
  --batch-size 50 \
  --lease-seconds 60 \
  --max-attempts 8
```

Options:

| Option | Meaning |
| --- | --- |
| `--batch-size N` | Maximum events claimed in this invocation. |
| `--lease-seconds N` | Claim duration before an abandoned claim becomes eligible again. |
| `--max-attempts N` | Attempt count at which a failed event becomes dead-lettered. |
| `--dry-run` | Print the eligible count without claiming or dispatching. |
| `--requeue-dead-letter UUID` | Return one matching dead-letter event to pending state. |

Normal output contains `claimed`, `dispatched`, `retried`, and `dead_lettered`
counts. Dry-run output contains `eligible`. A requeue prints the event UUID.
Normal dispatch fails explicitly when `DOCUMENT_EVENT_CALLBACK` is missing or
does not provide `handle(event)`.

### `reconcile_document_revisions`

Compares Django source revisions with an external indexed-revision reader:

```bash
cd src/django
uv run python manage.py reconcile_document_revisions --dry-run
```

Options:

| Option | Meaning |
| --- | --- |
| `--dry-run` | Report differences without requesting sync or deletion. |
| `--fail-on-item-error` | Exit unsuccessfully when one or more item requests fail. |

Output contains `source_count`, `indexed_count`, `requested_sync`,
`requested_delete`, `current`, and `failed`.

The command requires `DOCUMENT_RAG_REVISION_STATE_READER` with
`list_indexed()`. Non-dry-run execution also requires
`DOCUMENT_RAG_SYNC_COMMAND_SINK` with `request_sync(snapshot)` and
`request_delete(document_id)`. The repository defines these boundaries but does
not provide production RAG adapters.
