FROM python:3.11-slim-bullseye AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.5.31 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock* ./

FROM base AS builder
RUN uv sync --frozen --no-install-project
COPY . .
RUN uv sync --frozen

FROM builder AS development
RUN uv sync --frozen --group dev
EXPOSE 8090 5678
CMD ["/opt/venv/bin/python", "manage.py", "runserver", "0.0.0.0:8090"]

FROM builder AS production
RUN useradd --create-home --uid 10001 appuser
USER 10001:10001
EXPOSE 8090
CMD ["/opt/venv/bin/python", "manage.py", "runserver", "0.0.0.0:8090"]
