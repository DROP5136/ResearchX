# Performance

## Measured stages

Research jobs record stage progress for:

- planning → researching → evidence → fact checking → analysis → writing

Express SSE / status polling expose `progress`, `currentStage`, and elapsed time.

## Concurrency controls (env)

| Variable | Default | Purpose |
|----------|---------|---------|
| `MAX_CONCURRENT_RESEARCH` | 4 | Parallel background jobs per AI process |
| `MAX_CONCURRENT_SEARCH` | 5 | Search fan-out bound |
| `MAX_CONCURRENT_LLM_REQUESTS` / `MAX_CONCURRENT_AGENTS` | 4 / 3 | LLM / agent parallelism |
| `MAX_SOURCES` | 20 | Cap retrieved sources |
| `MAX_RESEARCH_ITERATIONS` | 2 | Iterative research loops |
| `MAX_SEARCH_QUERIES` | 20 | Query budget |
| `MAX_CHUNKS` / `MAX_CONTEXT_SIZE` / `MAX_LLM_CALLS` | 500 / 12k / 40 | RAG + LLM budgets |
| `MAX_PDF_PAGES` / `MAX_DOCUMENT_PAGES` | 200 | Document parse cap |

## Caching

1. File cache under `CACHE_PATH` (search HTML, search results).
2. Optional Redis L1 mirror (same keys, TTL).
3. Chroma embeddings reused per document id (skip re-embed when unchanged).

## Design rules

- Deterministic math / sorting / aggregation stays in Python.
- LLMs used for planning, extraction, reasoning, synthesis, writing.
- One failed optional source must not abort the whole job.
- HTTP retries only for transient errors (429 / 5xx / timeout) via tenacity.
