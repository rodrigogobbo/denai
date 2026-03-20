# ============================================================================
# DenAI — Multi-stage Docker build
# Usage: docker build -t denai .
# ============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder — install production dependencies
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

# Copy only dependency files first (better layer caching)
COPY pyproject.toml README.md LICENSE ./
COPY denai/ denai/

# Install production deps into a virtual‑env we can copy later
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir .

# ---------------------------------------------------------------------------
# Stage 2: Runtime — lean final image
# ---------------------------------------------------------------------------
FROM python:3.12-slim

# OCI labels
LABEL org.opencontainers.image.title="DenAI" \
      org.opencontainers.image.description="Your private AI den — local LLM assistant with tools, memory and zero cloud dependency." \
      org.opencontainers.image.source="https://github.com/rodrigogobbo/denai" \
      org.opencontainers.image.version="0.7.0"

# Install curl for healthcheck
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 denai \
    && useradd --uid 1000 --gid denai --create-home denai

# Copy virtual‑env from builder
COPY --from=builder /opt/venv /opt/venv

# Ensure venv binaries are on PATH
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Data directory for SQLite, configs, etc.
RUN mkdir -p /home/denai/.denai && chown -R denai:denai /home/denai/.denai

# Switch to non-root
USER denai
WORKDIR /home/denai

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

CMD ["python", "-m", "denai"]
