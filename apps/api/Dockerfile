FROM python:3.12-slim

WORKDIR /app

# Pull the latest Debian security patches for base-image OS packages, then
# upgrade pip/setuptools to current releases. This closes the fixable CVEs
# Trivy reports against the base image.
RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip setuptools

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml .
RUN uv sync --no-dev --no-editable

COPY src/ src/
COPY alembic.ini .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
