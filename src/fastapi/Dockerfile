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
EXPOSE 8099 5679
CMD ["/opt/venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8099", "--reload"]

FROM builder AS production
RUN useradd --create-home --uid 10002 appuser
USER 10002:10002
EXPOSE 8099
CMD ["/opt/venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8099"]
