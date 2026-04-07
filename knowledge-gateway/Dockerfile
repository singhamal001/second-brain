FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Minimal OS deps for psycopg2-binary compatibility and runtime TLS roots.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
COPY scripts ./scripts

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

RUN mkdir -p /data/vault

ENV VAULT_ROOT=/data/vault

EXPOSE 8080

CMD ["uvicorn", "knowledge_gateway.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]
