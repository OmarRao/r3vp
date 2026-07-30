FROM python:3.12-slim

WORKDIR /app

# Apply Debian security patches to base-image packages and install runtime
# dependencies, then upgrade pip/setuptools to close the fixable CVEs.
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
    openssh-client \
    age \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip setuptools

# Run as a dedicated non-root user (CWE-250: avoid running the container as root).
RUN useradd --create-home --uid 10001 appuser

# Pin sops to a specific release for reproducible builds (update deliberately).
ARG SOPS_VERSION=v3.13.3
RUN curl -fsSL "https://github.com/getsops/sops/releases/download/${SOPS_VERSION}/sops-${SOPS_VERSION}.linux.amd64" \
       -o /usr/local/bin/sops \
    && chmod +x /usr/local/bin/sops

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml .
# --no-cache: do not persist uv's download/build cache into the image. uv
# caches build-support packages (older setuptools, transitive msgpack) that the
# image scanner would otherwise flag even though they are not in the runtime
# venv. The venv itself is installed normally.
RUN uv sync --no-dev --no-editable --no-cache

COPY health_checks/ health_checks/
COPY src/ src/

RUN mkdir -p /certs /vault \
    && chown -R appuser:appuser /app /certs /vault
USER appuser

VOLUME ["/certs", "/vault"]

CMD ["uv", "run", "--no-sync", "python", "-m", "src.main"]
