FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY financial_research ./financial_research
COPY scripts ./scripts
COPY config ./config
COPY references ./references
COPY schemas ./schemas
COPY *.schema.json ./

RUN python3 -m pip install --no-cache-dir .

ENTRYPOINT ["fro-preflight"]
CMD ["--help"]
