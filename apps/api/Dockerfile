FROM python:3.12-slim

WORKDIR /app

# Pull the latest Debian security patches for base-image OS packages, then
# remove pip and setuptools. The application runs from the uv-managed venv and
# never needs pip at runtime; pip bundles vendored build-time dependencies
# (msgpack, setuptools) that the image scanner flags even though they are not
# in the runtime surface. Removing pip drops those findings and shrinks the
# attack surface. uv does not use pip, so builds are unaffected.
RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip uninstall -y pip setuptools wheel 2>/dev/null || true

# Run as a dedicated non-root user (CWE-250: avoid running the container as root).
RUN useradd --create-home --uid 10001 appuser

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml .
# --no-cache: do not persist uv's download/build cache into the image. uv
# caches build-support packages (older setuptools, transitive msgpack) that the
# image scanner would otherwise flag even though they are not in the runtime
# venv. The venv itself is installed normally.
RUN uv sync --no-dev --no-editable --no-cache

COPY src/ src/
COPY alembic.ini .

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
