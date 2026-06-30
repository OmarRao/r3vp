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

# Pin sops to a specific release for reproducible builds (update deliberately).
ARG SOPS_VERSION=v3.13.1
RUN curl -fsSL "https://github.com/getsops/sops/releases/download/${SOPS_VERSION}/sops-${SOPS_VERSION}.linux.amd64" \
       -o /usr/local/bin/sops \
    && chmod +x /usr/local/bin/sops

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml .
RUN uv sync --no-dev --no-editable

COPY health_checks/ health_checks/
COPY src/ src/

VOLUME ["/certs", "/vault"]

CMD ["uv", "run", "python", "-m", "src.main"]
