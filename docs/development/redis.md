# Redis

Redis is optional. MongoDB and local files hold durable research data.

## Uses

| Use | Key pattern |
|-----|-------------|
| Cache (search / pages) | `{namespace}:{hash}` |
| Short-lived job progress | `research:progress:{id}` |

## Not used for

- Final reports
- User accounts / JWT sessions
- Hard requirement for rate limiting

## Config

```bash
REDIS_URL=redis://127.0.0.1:6379/0
# leave empty to disable
```

If Redis is down or unset, the app continues with file cache and MongoDB.

Keep Redis private. Cache keys should not include emails or JWTs.
