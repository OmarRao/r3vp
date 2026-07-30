FROM python:3.12-slim

WORKDIR /app

# Pull the latest Debian security patches for base-image OS packages, then
# upgrade pip/setuptools to current releases. This closes the fixable CVEs
# Trivy reports against the base image.
RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip setuptools

# Run as a dedicated non-root user (CWE-250: avoid running the container as root).
RUN useradd --create-home --uid 10001 appuser

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml .
# Upgrade build/support packages that uv seeds into the resolved environment
# but does not pin in uv.lock, to their fixed releases, closing image-scanner
# findings (setuptools CVE-2025-47273 / CVE-2026-59890; msgpack GHSA-6v7p-g79w-8964).
RUN uv sync --no-dev --no-editable \
    && uv pip install --no-cache-dir --upgrade "setuptools>=83.0.0" "msgpack>=1.2.1"

COPY src/ src/
COPY alembic.ini .

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
