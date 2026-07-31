FROM python:3.12-slim

LABEL org.opencontainers.image.licenses="AGPL-3.0-only" \
      org.opencontainers.image.authors="Omar Rao"

WORKDIR /app

# Apply Debian security patches to base-image packages and install runtime
# dependencies, then remove pip and setuptools. The app runs from the
# uv-managed venv and never needs pip at runtime; pip bundles vendored
# build-time dependencies (msgpack, setuptools) that the image scanner flags
# even though they are not in the runtime surface. Removing pip drops those
# findings and shrinks the attack surface. uv does not use pip, so builds are
# unaffected.
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
    openssh-client \
    age \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip uninstall -y pip setuptools wheel 2>/dev/null || true

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
