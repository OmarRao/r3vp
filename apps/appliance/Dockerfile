FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    age \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN SOPS_VERSION=$(curl -s https://api.github.com/repos/getsops/sops/releases/latest | grep '"tag_name"' | cut -d'"' -f4) \
    && curl -fsSL "https://github.com/getsops/sops/releases/download/${SOPS_VERSION}/sops-${SOPS_VERSION}.linux.amd64" \
       -o /usr/local/bin/sops \
    && chmod +x /usr/local/bin/sops

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml .
RUN uv sync --no-dev --no-editable

COPY health_checks/ health_checks/
COPY src/ src/

VOLUME ["/certs", "/vault"]

CMD ["uv", "run", "python", "-m", "src.main"]
