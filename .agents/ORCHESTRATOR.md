# Main Thread Orchestration

Use subagents to design, review, and validate a production-ready Docker-based Python development environment. The main thread coordinates the work, waits for every requested subagent result, and returns only consolidated summaries.

## Agent Orchestration Logic: Dispatch & Context Loading
The Main Thread must dispatch three subagents in parallel. Before dispatching, the Main Thread must load the corresponding specification file from the .agents/ directory into the subagent's active context. This ensures the subagent's behavior, success criteria, and constraints are strictly bound to its assigned contract.

**Development-focused agent**: (Reference: .agents/AGENT_DEVELOPMENT.md)
**CI/CD-focused agent**: (Reference: .agents/AGENT_CICD.md)
**Production-focused agent**: (Reference: .agents/AGENT_PRODUCTION.md)

This is an implementation task. First use subagents to plan and identify risks. Create a plan for each subagent with a checklist, then execute the approved planned work in the current workspace. Wait for all subagents before consolidating, provide incremental summaries, ask for approval when creating and updating any files.

The main thread must explicitly wait until all requested subagents return before consolidating results. Do not produce the final answer early. If a subagent is still running, continue waiting or ask for permission to actively steer it.

The main thread may directly steer a running subagent, stop it, or close completed agent threads when needed.

## Agent Specification Registry
The following mapping defines the authoritative instruction sets for each subagent. The Main Thread is responsible for ensuring no subagent executes without its corresponding specification loaded.

| Subagent Role | Specification File Path | Context Priority |
| :--- | :--- | :--- |
| **Development** | `.agents/AGENT_DEVELOPMENT.md` | High (Local Dev Experience) |
| **CI/CD** | `.agents/AGENT_CICD.md` | High (Pipeline/Validation) |
| **Production** | `.agents/AGENT_PRODUCTION.md` | High (Security/Reliability) |


### Subagent Contract
Each subagent must declare:
- **Working directory**: Where operations should be performed
- **Required environment**: Dependencies, tools, or credentials needed
- **Timeout expectations**: Estimated duration and timeout handling
- **Success criteria**: Explicit definition of what "done" means
- **Failure modes**: How to handle partial failures or missing data
- **Authority Source**: The subagent must explicitly state which .agents/*.md specification file it is operating under in its initial "Action taken" summary.

### State Handling
- **Persistent state**: What files/artifacts survive between subagent calls
- **Shared state**: Which artifacts are passed between subagents
- **State validation**: How to verify previous subagent artifacts exist
- **Idempotency**: Operations that can be safely re-run

### Return Format and Structured Reporting
Subagents must return structured summaries of their work:
- **Action taken**: What was done
- **Artifacts created**: Files, configs, docs
- **Validations performed**: Tests, checks
- **Risks identified**: With severity ratings
- **Dependencies changed**: With rationale
- **Open questions**: Blocked decisions and open questions
- **Cross-agent impacts**: How changes affect others

### Peer Review Requirements
- **Self-review**: What subagent reviewed in their own work
- **Cross-review**: What other agents should verify
- **Security review**: For security-sensitive changes
- **Performance review**: For performance-sensitive changes

### Output Artifacts
Subagents must produce:
- **Files created/modified**: List with paths and brief description
- **Configuration changes**: Before/after for any config files
- **Dependencies added**: New packages with versions and rationale
- **Documentation updates**: What was created or updated
- **Validation results**: Summary of tests run and outcomes

### Rollback Planning
Subagents must:
- Define rollback procedure for their changes
- Test rollback before implementation
- Document rollback impact (data loss, downtime, etc.)
- Provide verification that rollback works

### Error Handling
- **Retry strategy**: Which errors are retryable and with what backoff
- **Partial success**: When to proceed vs. abort
- **Error reporting**: Required error summary format
- **Escalation**: When to return error to main thread vs. attempt self-correction

## Reasoning Effort
- **High reasoning effort:** architecture decisions, security reviews, compliance validation, production risk assessment, reliability trade-offs.
- **Medium reasoning effort:** implementation details, Docker/Compose structure, CI/CD structure, deployment workflow design, dependency management.
- **Low reasoning effort:** documentation review, file structure validation, naming checks, formatting checks, simple consistency checks.

## Execution Decisions
This scaffold must be implemented with **Docker Compose only**. Do not use Kubernetes, Helm, Kustomize, Argo Rollouts, or Kubernetes-specific deployment manifests.

Use GitHub Actions as the canonical CI/CD system. Workflows must run in GitHub-hosted CI and must also be runnable locally with `act`.

CI/CD checks should be exposed through shared local commands via `make`:
- `make lint`, `make test`, `make test-integration`, `make scan`, `make compose-check`, `make ci`, `make act-ci`.

### Project Isolation and Dependency Ownership
FastAPI and Django must be treated as independent Python projects. The root of
the repository may contain orchestration tooling only; it must not be the shared
runtime dependency owner for both services.

Required service-local dependency artifacts:
- Django: `src/django/pyproject.toml` and `src/django/uv.lock`.
- FastAPI: `src/fastapi/pyproject.toml` and `src/fastapi/uv.lock`.

Isolation requirements:
- Django runtime dependencies must not include FastAPI-only packages.
- FastAPI runtime dependencies must not include Django-only packages.
- Service Dockerfiles must copy and install from their own service-local
  `pyproject.toml` and `uv.lock`.
- Docker Compose build contexts must be service-local unless a task explicitly
  documents why repository-root context is required.
- GitHub image publishing must build Django and FastAPI from their independent
  service Dockerfiles and dependency locks.
- Root-level tooling may provide shared `make` commands, repository-contract
  tests, lint orchestration, and documentation checks, but must not collapse the
  services back into one Python runtime project.
- If a root `pyproject.toml` exists, it must be limited to repository-level
  tooling and must not define Django or FastAPI application runtime dependencies.

### Environment Validation
- **Required tools**: `docker`, `docker compose`, `uv`, `act`, `make`
- **Version requirements**: Specific version constraints
- **Network access**: Firewall/proxy requirements
- **Credentials**: Required access tokens and permissions

### Dependency Contracts
- **Dev agent**: What CI/CD needs from Dev (test commands, compose files)
- **CI/CD agent**: What Production needs from CI/CD (images, artifacts)
- **Shared artifacts**: What files/services are shared and version expectations
- **Service dependency ownership**: Dev and CI/CD must cross-check that Django
  and FastAPI remain independently installable, testable, buildable, and
  lockable via their service-local `pyproject.toml` and `uv.lock`.

### Validation Gates
Each agent must validate:
- **Before starting**: Preconditions are met
- **During work**: Intermediate validation checkpoints
- **After completion**: All success criteria met
- **Cross-check**: Verify other agents' assumptions

## Core Requirements (The Blueprint)

### Technical Stack
- **Base Image**: A single portable Python 3.11 slim-bullseye base image.
- **Django**: Port `8090` with a default scaffold.
- **FastAPI**: Port `8099` with async support.
- **Reverse Proxy**: Caddy on ports `80` and `443` with routing and security.
- **PostgreSQL**: 15+ per service with connection pooling and replication for production-like environments.
- **Redis**: Sentinel for high-availability caching and session storage in production-like environments.

### Testing & Quality
- **Unit/Integration/E2E/Performance/Security tests** required for new code.
- **Security**: Audit for secrets exposure, permission changes, and dependency vulnerabilities.
- **Dependency Management**: Use `uv` with service-local locks
  (`src/django/uv.lock`, `src/fastapi/uv.lock`) and optimize Docker layer
  caching around each service's own lockfile.

### Documentation
- Required: README, Onboarding, Operations, API, and Architecture docs.

## Post-Execution Consolidation
The final consolidated response must include:
- Overall architecture summary.
- Development, CI/CD, and Production summaries.
- Cross-agent conflicts or trade-offs.
- Final recommendations and remaining blockers.

## Cleanup and Teardown
- Clean temporary files and service containers.
- Remove test/development volumes and reset test state.

## File Tree
.
├── .agents/                         # Documentation for the agents themselves
│   ├── ORCHESTRATOR.md             # The main orchestration logic
│   ├── AGENT_DEVELOPMENT.md        # Dev agent specs
│   ├── AGENT_CICD.md               # CI/CD agent specs
│   └── AGENT_PRODUCTION.md         # Production agent specs
├── .docker/                    # Shared Docker utilities/scripts
│   ├── scripts/                     # Helper scripts (e.g., seed_db.sh)
│   └── compose/                     # Shared base compose fragments
├── .github/
│   └── workflows/                   # GitHub Actions (CI/CD Agent's domain)
│       ├── ci.yml
│       ├── deploy-staging.yml
│       └── deploy-production.yml
├── config/                          # Environment-specific configurations
│   ├── caddy/                       # Caddyfile and routing rules
│   ├── postgres/                    # SQL init scripts, custom configs
│   └── redis/                       # Sentinel and persistence configs
├── docs/                            # User-facing documentation
│   ├── architecture/               # High-level system design
│   ├── onboarding/                 # Setup instructions
│   └── operations/                 # Runbooks and deployment guides
├── src/                            # Business logic (Service Layer)
│   ├── django/                  # Django web framework service and application
│   │   ├── app/                     # Python source code
│   │   ├── tests/                   # Unit and integration tests
│   │   ├── Dockerfile               # Multi-stage (Dev/Builder/Prod targets)
│   │   ├── pyproject.toml           # Django project metadata and dependencies
│   │   └── uv.lock                  # Django deterministic dependency lock
│   └── fastapi/                 # FastAPI web framework service and application
│       ├── app/                    # Python source code
│       ├── tests/
│       ├── Dockerfile               # Multi-stage (Dev/Builder/Prod targets)
│       ├── pyproject.toml           # FastAPI project metadata and dependencies
│       └── uv.lock                  # FastAPI deterministic dependency lock
├── .env.dev                    # Local development secrets
├── .env.staging                 # Staging environment secrets
├── .env.prod                    # Production secrets (never committed)
├── Makefile                       # The "Interface" for all agents (make test, make scan, etc.)
├── pyproject.toml                   # Optional repo tooling only; no app runtime deps
├── uv.lock                          # Optional repo tooling lock only
├── docker-compose.yml               # Base services (Postgres, Redis, Caddy)
├── docker-compose.dev.yml           # Dev overrides (Volumes, debug ports)
├── docker-compose.staging.yml      # Staging overrides
└── docker-compose.prod.yml          # Prod overrides (Hardened, no volumes)


## Service Source Layout

Django must use `src/django/app` as its Python application package.
Do not rename the Django package to `django_app`, `project`, `core`, or any other name.

FastAPI must use `src/fastapi/app` as its Python application package.
Do not rename the FastAPI package to `fastapi_app`, `project`, `core`, or any other name.

Because Django and FastAPI are independent Python projects with separate
`pyproject.toml` and `uv.lock` files, both services may use an `app` package
name without import collisions. Tests, Dockerfiles, and Compose commands must
execute within each service project context.

Validation must fail if `src/django/django_app` exists, if Django settings
reference `django_app.settings`, if `src/fastapi/fastapi_app` exists, or if
FastAPI commands reference `fastapi_app.main:app`.
