# Repository Verification Hardening Design

## Objective

Make the repository's documented quality claims enforceable by CI, document
every supported API interface, eliminate known high-severity production
frontend dependency advisories, and publish an SRS that accurately reflects the
resulting project state.

## Scope

This change is limited to:

- frontend lint, test, build, and production dependency verification in CI;
- correction of existing frontend test failures required to make that CI gate
  reliable;
- complete documentation of the current Django, FastAPI, Next.js, document,
  CSRF, error, and document-integration command interfaces;
- patch-level remediation of production npm dependency advisories;
- publication of the SRS, its document/RAG architecture guide, and the
  architecture documentation index; and
- SRS corrections needed to keep requirement statuses aligned with the code.

`Archive.zip`, `.git.broken-worktree-pointer-20260724`, and unrelated working
tree changes are outside scope.

## CI Architecture

GitHub Actions will use independent backend and frontend jobs so each technology
stack has explicit setup, caching, logs, and failure ownership.

The backend job will retain the existing Python, Docker Buildx, and `uv`
workflow and invoke a backend-specific Make target. The frontend job will:

1. install Node.js 22, matching the frontend Dockerfile;
2. cache npm downloads using `src/frontend/package-lock.json`;
3. install exactly the locked dependency graph with `npm ci`;
4. run the TypeScript check;
5. run the complete Vitest suite;
6. build the production Next.js application; and
7. fail on high- or critical-severity production dependency advisories.

The Makefile will expose backend and frontend CI targets for reproducible local
execution while retaining an aggregate target for developers who want to run
both stacks.

## Frontend Test Reliability

The current complete frontend suite will be reproduced in a clean dependency
environment. Any failure will be traced to its root cause before modification.
A behavioral change will use a regression-first test cycle; a test-isolation
problem will be corrected at the shared setup or fixture boundary rather than
hidden with retries, ordering, or exclusions.

CI will always run the full suite. Document-only test selection is not an
acceptable substitute.

## API Documentation

`docs/API.md` will become the canonical human-readable API reference for the
implemented scaffold. It will document:

- service base URLs and reverse-proxy routing;
- Django health, session, example mutation, mock chat, and document endpoints;
- FastAPI root, health, readiness, and generated OpenAPI endpoints;
- the Next.js frontend health and interactions-chat handlers;
- document list query parameters and supported ordering values;
- upload, detail, metadata update, file replacement, download, and deletion
  request/response contracts;
- multi-file and partial-success behavior;
- CSRF acquisition and submission;
- the stable error envelope and known error codes;
- authentication limitations; and
- document outbox dispatch and revision reconciliation management commands.

Examples will use valid JSON and representative curl commands without implying
that future RAG adapters or authentication already exist.

## Dependency Security

The direct Next.js dependency will be upgraded to the smallest patched,
compatible release that resolves the reported advisory. The npm lockfile will be
regenerated through npm rather than edited manually.

The remediated graph must satisfy:

```text
npm audit --omit=dev --audit-level=high
```

The production build and complete frontend test suite must remain green after
the upgrade. Major-version upgrades and unrelated dependency refreshes are out
of scope.

## SRS Alignment

The final documentation commit will include:

- `SOFTWARE_REQUIREMENTS_SPECIFICATION.md`;
- `docs/architecture/document-file-handling-and-rag-readiness.md`; and
- the corresponding link in `docs/architecture/README.md`.

The SRS will be adjusted to:

- distinguish the service-level optional initial-title capability from the
  public upload API;
- require and record full frontend CI verification;
- require high-severity production dependency audit enforcement;
- reflect the completed API reference; and
- retain all unimplemented RAG capabilities as future requirements.

## Commit Strategy

Changes will be committed in independently reviewable units:

1. design documentation;
2. implementation plan;
3. frontend CI verification and any necessary test-reliability correction;
4. complete API documentation;
5. production dependency remediation and audit enforcement; and
6. SRS and supporting architecture documentation.

Each implementation commit will be verified before moving to the next task.
The complete repository will receive a final fresh verification before
`feature/rag` is pushed to `origin`.

## Acceptance Criteria

The work is complete when:

- frontend CI performs a locked install, type check, complete test run,
  production build, and production dependency audit;
- the full frontend suite passes without exclusions or retries;
- the frontend production build succeeds;
- the production npm audit reports no high- or critical-severity findings;
- `docs/API.md` describes every current application API and integration command;
- the SRS and architecture references are internally consistent;
- backend verification remains green;
- each requested concern has an isolated commit;
- `Archive.zip` remains present and uncommitted; and
- `origin/feature/rag` contains all intended commits.
