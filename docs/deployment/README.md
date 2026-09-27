# Deployment

Recommended production layout:

| Service | Port | Notes |
|---------|------|--------|
| web | 80/443 | Static build behind nginx |
| server | 5000 | Set strong `JWT_SECRET`, Atlas `MONGODB_URI` |
| ai-service | 8000 | Provide LLM/search keys; mount `data/` volume |
| mongodb | 27017 | Managed Atlas preferred |

Use `docker compose up --build` for a local full stack. Point `FASTAPI_URL` at the AI service hostname inside the compose network. Do not expose AI service publicly if Express is the only consumer.
