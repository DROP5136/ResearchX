# Performance

## Stages

Planning → research → evidence → fact check → analysis → writing

Progress is exposed via status / SSE (`progress`, `currentStage`, elapsed time).

## Limits (env)

| Variable | Default |
|----------|---------|
| `MAX_CONCURRENT_RESEARCH` | 4 |
| `MAX_CONCURRENT_SEARCH` | 5 |
| `MAX_CONCURRENT_AGENTS` | 3 |
| `MAX_SOURCES` | 20 |
| `MAX_RESEARCH_ITERATIONS` | 2 |
| `MAX_SEARCH_QUERIES` | 20 |
| `MAX_CHUNKS` / `MAX_CONTEXT_SIZE` / `MAX_LLM_CALLS` | 500 / 12k / 40 |
| `MAX_PDF_PAGES` | 200 |

## Caching

File cache under `CACHE_PATH`, optional Redis mirror, Chroma embeddings reused per document id.

## Notes

- Math / sorting / aggregation stay in Python
- LLMs are used for planning, extraction, reasoning, and writing
- One failed optional source should not abort the whole run
- Retries target transient HTTP errors (429 / 5xx / timeout)
