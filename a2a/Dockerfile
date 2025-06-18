# this Dockerfile should be built from the repo root
FROM python:3.13.1-slim-bookworm

ENV PYTHONUNBUFFERED=True
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-install-workspace

COPY . /app
RUN uv sync --frozen

CMD ["/app/.venv/bin/python", "/app/a2a/weather"]