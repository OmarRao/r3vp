FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    sops \
    age \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml .
RUN uv sync --no-dev --no-editable

COPY health_checks/ health_checks/
COPY src/ src/

VOLUME ["/certs", "/vault"]

CMD ["uv", "run", "python", "-m", "src.main"]
