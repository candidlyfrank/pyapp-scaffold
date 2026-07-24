# Repository Verification Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce frontend quality and production dependency checks in CI, publish a complete API reference, remediate known production npm advisories, and commit an accurate SRS with its supporting architecture documentation.

**Architecture:** Keep backend and frontend verification in independent GitHub Actions jobs with matching Make targets. Treat `docs/API.md` as the canonical implemented-interface reference, npm's lockfile and audit result as the production dependency source of truth, and the SRS plus architecture guide as the requirements baseline.

**Tech Stack:** GNU Make, GitHub Actions, Node.js 22, npm, Next.js 16, TypeScript, Vitest, Django, FastAPI, pytest, Markdown.

## Global Constraints

- Use Node.js 22 in CI to match `src/frontend/Dockerfile`.
- Install frontend dependencies with `npm ci` from `src/frontend/package-lock.json`.
- Run the complete frontend suite without retries, exclusions, or test-order dependencies.
- Fail CI on high- or critical-severity production npm advisories.
- Use the smallest compatible patched Next.js release; do not perform a major-version upgrade.
- Do not stage or modify `Archive.zip` or `.git.broken-worktree-pointer-20260724`.
- Commit each implementation concern independently.
- Push only after a fresh complete verification.

---

### Task 1: Frontend CI Verification

**Files:**
- Modify: `tests/test_repository_contract.py`
- Modify: `src/frontend/app/chat/components/InteractionsWorkspace.test.tsx`
- Modify: `Makefile`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: existing `npm run lint`, `npm test`, and `npm run build` scripts from `src/frontend/package.json`.
- Produces: `make ci-backend` and `make ci-frontend` targets; independent `backend` and `frontend` GitHub Actions jobs.

- [ ] **Step 1: Add failing repository contract expectations**

Update `test_required_make_targets_exist` to require `ci-backend` and
`ci-frontend`. Replace `test_workflows_delegate_to_shared_make_commands` with
assertions that require:

```python
def test_workflows_delegate_to_shared_make_commands():
    ci = read(".github/workflows/ci.yml")
    publish = read(".github/workflows/publish.yml")
    deploy = read(".github/workflows/deploy.yml")
    rollback = read(".github/workflows/rollback.yml")

    assert "uv sync --locked --group dev --project src/django" in ci
    assert "uv sync --locked --group dev --project src/fastapi" in ci
    assert "make ci-backend" in ci
    assert "actions/setup-node@v4" in ci
    assert "node-version: 22" in ci
    assert "cache-dependency-path: src/frontend/package-lock.json" in ci
    assert "make ci-frontend" in ci
    assert "context: ./src/django" in publish
    assert "context: ./src/fastapi" in publish
    assert "make compose-check" in deploy
    assert "make rollback" in rollback
```

- [ ] **Step 2: Verify the repository contract fails**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run pytest tests/test_repository_contract.py -q
```

Expected: failure because `ci-backend`, `ci-frontend`, `actions/setup-node@v4`,
and the new Make invocations do not yet exist.

- [ ] **Step 3: Correct stale interaction workspace tests**

Update the empty-shell expectation to the three enabled capabilities:

```typescript
for (const label of ["Swarm", "Deep Research", "Docs"]) {
  expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
}
```

Use the enabled Docs capability in the prompt test:

```typescript
await user.click(screen.getByRole("button", { name: "Docs" }));
expect(screen.getByLabelText("Message")).toHaveValue(
  "Draft a concise project brief with next steps",
);
```

Update both message assertions and the expected request body to use
`"Draft a concise project brief with next steps"`.

Replace the stale authenticated-utility test with:

```typescript
it("hides account-only utilities from anonymous users", () => {
  render(<InteractionsWorkspace />);

  expect(screen.queryByRole("button", { name: "Help" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Settings" })).not.toBeInTheDocument();
});
```

- [ ] **Step 4: Verify the corrected frontend test file**

Run in a clean Node 22 environment:

```bash
docker run --rm \
  -v "$PWD/src/frontend:/source:ro" \
  -w /work node:22-alpine \
  sh -lc 'cp -a /source/. /work/ && npm ci --ignore-scripts && npm test -- app/chat/components/InteractionsWorkspace.test.tsx'
```

Expected: 7 tests pass.

- [ ] **Step 5: Add backend and frontend Make targets**

Keep the existing Python commands under a new `ci-backend` target and add:

```make
ci-backend: lint test test-integration scan compose-check

ci-frontend:
	cd src/frontend && npm ci
	cd src/frontend && npm run lint
	cd src/frontend && npm test
	cd src/frontend && npm run build

ci: ci-backend ci-frontend
```

- [ ] **Step 6: Split the GitHub Actions workflow**

Rename the current job to `backend`, change its final command to
`make ci-backend`, and add:

```yaml
  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: src/frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
          cache-dependency-path: src/frontend/package-lock.json
      - run: npm ci
      - run: npm run lint
      - run: npm test
      - run: npm run build
```

The workflow uses direct npm commands for readable GitHub step output; the
Makefile target remains the local aggregate.

- [ ] **Step 7: Verify contracts and frontend quality**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run pytest tests/test_repository_contract.py -q
docker run --rm \
  -v "$PWD/src/frontend:/source:ro" \
  -w /work node:22-alpine \
  sh -lc 'cp -a /source/. /work/ && npm ci --ignore-scripts && npm run lint && npm test && npm run build'
```

Expected: repository contracts pass; 39 frontend tests pass; TypeScript and the
production build exit successfully.

- [ ] **Step 8: Commit frontend CI verification**

```bash
git add tests/test_repository_contract.py \
  src/frontend/app/chat/components/InteractionsWorkspace.test.tsx \
  Makefile .github/workflows/ci.yml
git commit -m "ci(frontend): enforce complete verification"
```

---

### Task 2: Complete API Documentation

**Files:**
- Modify: `tests/test_repository_contract.py`
- Modify: `docs/API.md`

**Interfaces:**
- Consumes: implemented routes in `src/django/app/urls.py`, `src/django/documents/urls.py`, `src/fastapi/app/api/routes/system.py`, and `src/frontend/app/**/route.ts`.
- Produces: canonical current-interface documentation in `docs/API.md`.

- [ ] **Step 1: Add a failing API documentation contract**

Add:

```python
def test_api_reference_documents_supported_interfaces():
    api = read("docs/API.md")
    required_interfaces = [
        "GET /api/session/",
        "POST /api/example-mutation/",
        "POST /api/chat",
        "GET /api/documents/",
        "POST /api/documents/",
        "GET /api/documents/{id}/",
        "PATCH /api/documents/{id}/",
        "DELETE /api/documents/{id}/",
        "GET /api/documents/{id}/download/",
        "GET /api/health",
        "POST /chat/api/chat",
        "dispatch_document_outbox",
        "reconcile_document_revisions",
        "X-CSRFToken",
        "207 Multi-Status",
    ]
    for interface in required_interfaces:
        assert interface in api
```

- [ ] **Step 2: Verify the documentation contract fails**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run pytest tests/test_repository_contract.py::test_api_reference_documents_supported_interfaces -q
```

Expected: failure on the first undocumented interface.

- [ ] **Step 3: Rewrite the API reference**

Structure `docs/API.md` with these exact top-level sections:

```markdown
# API Reference

## Service Routing
## Authentication and CSRF
## Error Format
## Django API
## Document API
## FastAPI
## Next.js Route Handlers
## Document Integration Commands
```

Document all routes from the task's consumed route files, including methods,
status codes, query parameters, request media types, JSON shapes, partial upload
results, supported ordering values, validation limits, CSRF flow, and the
unauthenticated/local-development limitation. Include example invocations for
JSON metadata update, multipart replacement, outbox dispatch, dead-letter
requeue, and revision reconciliation.

- [ ] **Step 4: Verify documentation coverage and formatting**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run pytest tests/test_repository_contract.py -q
git diff --check -- docs/API.md tests/test_repository_contract.py
```

Expected: all repository contract tests pass and no whitespace errors are
reported.

- [ ] **Step 5: Commit the API reference**

```bash
git add docs/API.md tests/test_repository_contract.py
git commit -m "docs(api): document implemented interfaces"
```

---

### Task 3: Production Dependency Remediation

**Files:**
- Modify: `tests/test_repository_contract.py`
- Modify: `src/frontend/package.json`
- Modify: `src/frontend/package-lock.json`
- Modify: `.github/workflows/ci.yml`
- Modify: `Makefile`

**Interfaces:**
- Consumes: npm registry advisory data and the Node 22 frontend toolchain.
- Produces: Next.js 16.2.11 locked dependency graph and `npm audit --omit=dev --audit-level=high` CI gate.

- [ ] **Step 1: Add failing dependency policy contracts**

Add imports and a test:

```python
import json


def test_frontend_production_dependencies_are_audited():
    package = json.loads(read("src/frontend/package.json"))
    ci = read(".github/workflows/ci.yml")
    makefile = read("Makefile")

    assert package["dependencies"]["next"] == "16.2.11"
    assert "npm audit --omit=dev --audit-level=high" in ci
    assert "npm audit --omit=dev --audit-level=high" in makefile
```

- [ ] **Step 2: Verify the dependency policy contract fails**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run pytest tests/test_repository_contract.py::test_frontend_production_dependencies_are_audited -q
```

Expected: failure because Next.js is 16.2.10 and no production audit gate exists.

- [ ] **Step 3: Upgrade through npm**

Run in a writable isolated checkout of the frontend directory:

```bash
npm install --save-exact next@16.2.11
```

Copy only the resulting `package.json` and `package-lock.json` changes back to
`src/frontend`. Do not manually edit lockfile integrity or resolved fields.

- [ ] **Step 4: Add the production audit gate**

Append this command to `ci-frontend` after `npm ci` and add the same command to
the frontend GitHub Actions job immediately after its install step:

```text
npm audit --omit=dev --audit-level=high
```

- [ ] **Step 5: Verify dependency policy and runtime security**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run pytest tests/test_repository_contract.py -q
docker run --rm \
  -v "$PWD/src/frontend:/source:ro" \
  -w /work node:22-alpine \
  sh -lc 'cp -a /source/. /work/ && npm ci --ignore-scripts && npm audit --omit=dev --audit-level=high && npm run lint && npm test && npm run build'
```

Expected: repository contracts pass; npm reports zero high/critical production
advisories; 39 tests pass; TypeScript and production build succeed.

- [ ] **Step 6: Review the lockfile delta**

Run:

```bash
git diff -- src/frontend/package.json src/frontend/package-lock.json
```

Expected: only Next.js and transitive packages required by the patch upgrade
change; no unrelated major dependency refresh occurs.

- [ ] **Step 7: Commit dependency remediation**

```bash
git add tests/test_repository_contract.py src/frontend/package.json \
  src/frontend/package-lock.json .github/workflows/ci.yml Makefile
git commit -m "fix(frontend): remediate production advisories"
```

---

### Task 4: SRS and Architecture Baseline

**Files:**
- Modify: `tests/test_repository_contract.py`
- Create: `SOFTWARE_REQUIREMENTS_SPECIFICATION.md`
- Create: `docs/architecture/document-file-handling-and-rag-readiness.md`
- Modify: `docs/architecture/README.md`

**Interfaces:**
- Consumes: completed CI, API reference, dependency policy, document API, and integration command behavior.
- Produces: tracked requirements baseline and non-broken architecture documentation links.

- [ ] **Step 1: Add a failing documentation-baseline contract**

Add:

```python
def test_document_rag_requirements_baseline_is_tracked_and_linked():
    srs = read("SOFTWARE_REQUIREMENTS_SPECIFICATION.md")
    architecture_index = read("docs/architecture/README.md")
    architecture_guide = read(
        "docs/architecture/document-file-handling-and-rag-readiness.md"
    )

    assert "## 11. Test Requirements" in srs
    assert "frontend verification job" in srs
    assert "production dependency" in srs
    assert "docs/API.md" in srs
    assert "Document file handling and RAG readiness" in architecture_index
    assert "# Document File Handling and RAG Readiness" in architecture_guide
```

- [ ] **Step 2: Verify the baseline contract fails**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run pytest tests/test_repository_contract.py::test_document_rag_requirements_baseline_is_tracked_and_linked -q
```

Expected: failure because the SRS does not yet contain the new CI and dependency
requirements.

- [ ] **Step 3: Align the SRS status and requirements**

Make these requirement-level changes while retaining stable IDs:

```markdown
| FR-CRE-002 | Partial | The initial title SHALL default to the validated filename stem. The service layer MAY accept an explicit valid title; the current public multi-file upload API does not expose that option. |
```

Add implemented requirements stating that:

- the frontend verification job performs locked install, type checking, the
  complete test suite, and a production build;
- CI audits production frontend dependencies and fails at high severity; and
- the implemented API reference documents the current HTTP and management
  command interfaces.

Add the frontend verification job and production dependency audit to baseline
acceptance and traceability. Do not mark authentication, scheduling, extraction,
embedding, vector search, generation, backup automation, or other future RAG
capabilities as implemented.

- [ ] **Step 4: Review the architecture documents**

Confirm that the guide:

- treats Django as the document source of truth;
- treats RAG as a downstream concern;
- describes revision/checksum/outbox/reconciliation boundaries;
- does not claim that extraction, embeddings, vector storage, or generation
  already exist; and
- is linked from `docs/architecture/README.md`.

Correct only statements that conflict with the current code or updated SRS.

- [ ] **Step 5: Verify documentation consistency**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run pytest tests/test_repository_contract.py -q
rg -n "TBD|TODO|implement later" \
  SOFTWARE_REQUIREMENTS_SPECIFICATION.md \
  docs/architecture/document-file-handling-and-rag-readiness.md
git diff --check -- \
  SOFTWARE_REQUIREMENTS_SPECIFICATION.md \
  docs/architecture/README.md \
  docs/architecture/document-file-handling-and-rag-readiness.md \
  tests/test_repository_contract.py
```

Expected: repository contracts pass, the placeholder search returns no matches,
and no whitespace errors are reported.

- [ ] **Step 6: Commit the requirements baseline**

```bash
git add SOFTWARE_REQUIREMENTS_SPECIFICATION.md \
  docs/architecture/README.md \
  docs/architecture/document-file-handling-and-rag-readiness.md \
  tests/test_repository_contract.py
git commit -m "docs(rag): publish requirements baseline"
```

Confirm before committing:

```bash
git diff --cached --name-only
```

Expected: exactly the four paths listed above; neither `Archive.zip` nor the
worktree recovery pointer appears.

---

### Task 5: Final Repository Verification and Push

**Files:**
- Verify only; no source changes expected.

**Interfaces:**
- Consumes: all four implementation commits and existing backend verification.
- Produces: pushed `origin/feature/rag` whose remote tip equals local HEAD.

- [ ] **Step 1: Run backend verification**

Run:

```bash
make ci-backend
```

Expected: Ruff, contract tests, Django tests, FastAPI tests, security scans, and
Compose validation all exit successfully.

- [ ] **Step 2: Run frontend verification from a clean install**

Run:

```bash
docker run --rm \
  -v "$PWD/src/frontend:/source:ro" \
  -w /work node:22-alpine \
  sh -lc 'cp -a /source/. /work/ && npm ci --ignore-scripts && npm audit --omit=dev --audit-level=high && npm run lint && npm test && npm run build'
```

Expected: audit passes at high severity, 39 tests pass, TypeScript succeeds, and
the production build exits successfully.

- [ ] **Step 3: Verify repository state and commit boundaries**

Run:

```bash
git status --short --branch
git log --oneline --decorate -6
git diff --check HEAD~6..HEAD
test -f Archive.zip
git ls-files --error-unmatch Archive.zip
```

Expected: intended commits are present; `Archive.zip` exists. The final
`git ls-files` command is expected to fail, proving the archive remains
untracked.

- [ ] **Step 4: Push the branch**

Run:

```bash
git push origin feature/rag
```

Expected: `origin/feature/rag` advances to local `feature/rag`.

- [ ] **Step 5: Verify the remote tip**

Run:

```bash
git fetch origin feature/rag
test "$(git rev-parse feature/rag)" = "$(git rev-parse origin/feature/rag)"
```

Expected: both revisions are identical.
