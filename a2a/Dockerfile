# this Dockerfile should be built from the repo root
FROM python:3.13.1-slim-bookworm

ENV PYTHONUNBUFFERED=True
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-install-workspace --package a2a

COPY ./a2a /app/a2a
COPY ./common /app/common
RUN uv sync --frozen --package=a2a

CMD ["/app/.venv/bin/python", "/app/a2a/agents/restatedev"]