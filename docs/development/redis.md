# Redis (optional)

Redis is an **optional** acceleration layer. MongoDB + local files remain the source of truth for research results.

## What Redis is used for

| Use | Key pattern | Notes |
|-----|-------------|--------|
| Search / page / embedding cache mirror | `{namespace}:{hash}` | File cache is durable; Redis is L1 |
| Short-lived job progress | `research:progress:{id}` | TTL; never the only copy of results |

## What Redis is NOT used for

- Permanent research reports
- User accounts / JWT sessions
- Mandatory rate limiting (Express rate limits stay in-memory so Redis outages cannot weaken them)

## Configuration

```bash
REDIS_URL=redis://127.0.0.1:6379/0   # AI service
REDIS_URL=redis://127.0.0.1:6379/1   # Express (optional)
# or leave empty to disable
```

## Failure behavior

If Redis is unset or unreachable:

1. Connection attempts soft-fail and disable further tries for the process lifetime.
2. File cache / Mongo continue normally.
3. `/ready` still returns ready (Redis marked optional).
4. Research jobs still persist to `data/outputs` and Mongo.

## Security

- Do not expose Redis to the public internet.
- Do not put user emails or JWTs into shared cache keys — keys are content hashes / research ids only.
