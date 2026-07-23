# pyapp-scaffold

Docker Compose scaffold for a server-rendered frontend and two Python services:

- Next.js frontend on `localhost:3000` in development
- Django on `localhost:8090`
- FastAPI on `localhost:8099`
- Caddy reverse proxy on ports `80` and `443`
- PostgreSQL 15 per service
- Redis for cache/session-style dependencies

## Prerequisites

- Docker and Docker Compose
- `uv`
- `make`
- `act` for local GitHub Actions checks

## Start Development

```sh
uv sync --locked --group dev
make up
```

Open:

- Integrated frontend: `https://pyapp.envx/`
- Authenticated SSR example: `https://pyapp.envx/account`
- Integrated Django admin: `https://pyapp.envx/admin/`
- Caddy ingress health: `https://pyapp.envx/health`
- Direct frontend debugging: `http://localhost:3000/`
- Django app: `http://localhost:8090/`
- Django health: `http://localhost:8090/health/`
- FastAPI app: `http://localhost:8099/`
- FastAPI health: `http://localhost:8099/health`
- FastAPI readiness: `http://localhost:8099/ready`
- FastAPI docs: `http://localhost:8099/docs`
- Django admin: `http://localhost:8090/admin/`
- Caddy FastAPI route: `http://localhost/fastapi/health`

### Kimi-style interactions demo

Open `http://localhost:3000/chat` for an isolated, original Kimi-style
interface reference. Its mock chat transport is `POST /interactions/api/chat`,
selected attachments stay in the browser and are not uploaded, and its local
history/preferences use dedicated `kimi.interactions.*` keys. The existing
`/chat` route and Django chat API remain independent.

Browser code calls Django through relative `/api/...` paths. Server-rendered frontend code uses the private `DJANGO_INTERNAL_URL=http://django:8090` and forwards only the incoming cookie header to that configured origin.

The frontend process health endpoint is `http://frontend:3000/api/health` on the private Compose network. It intentionally remains independent of Django; Caddy reserves public `/api/*` paths for Django.

### Document upload and library

The document workspace uses live Django API data through the Caddy origin:

- `https://pyapp.envx/documents/upload` uploads one or more documents.
- `https://pyapp.envx/documents` searches, filters, and sorts the library.
- `https://pyapp.envx/documents/{id}` edits metadata, replaces files, downloads, and deletes.

Use the Caddy URL for document operations because it serves Next.js and proxies
relative `/api/...` requests to Django on the same origin.

Phase one accepts PDF, DOCX, UTF-8 TXT, Markdown, and CSV files up to 25 MB
each. Django validates file contents rather than trusting browser MIME metadata.
Document metadata is stored in a dedicated SQLite database, while existing
Django apps continue using PostgreSQL.

Persistent local document data is stored beneath:

```text
src/django/.data/documents/
├── metadata.sqlite3
└── files/
```

Initialize both Django databases with:

```sh
make migrate
```

Before starting the hardened production Compose profile, initialize the
project-local bind mount so Django's non-root UID can write SQLite and files:

```sh
make document-storage-init
```

`make prod-up` runs this initialization automatically.

The document database can later be moved to PostgreSQL by changing the
`documents` database alias and migrating its ORM data; the API and Next.js
routes do not need to change.

> **Security:** The document workspace is intentionally unauthenticated for
> local development. Add authentication, ownership, and authorization checks
> before exposing it publicly.

### Document integration workflows

The document app records lifecycle changes in its own transactional outbox.
It does not import or require a RAG implementation.

This project ships no scheduler, external provider, or RAG implementation;
application owners must implement, configure, and operate future adapters.

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
reconciliation is an independent consistency repair mechanism. Failed callback
deliveries retry with bounded backoff and eventually become dead letters, which
can be requeued through the dispatch command. Run `make migrate` before these
workflows so the documents outbox schema is available.

## Validate

```sh
make ci
```

The shared CI entrypoint runs linting, tests, security checks, and Compose config validation.
