# Docker and Cloud Deployment Guide

## Local Docker architecture

The local deployment uses two containers:

- **Backend:** Python 3.14 slim image, UV-managed dependencies, FastAPI served by Uvicorn at port 8000.
- **Frontend:** multi-stage Node 22 build, then Nginx serves the Vite `dist` output at port 80.

The root `docker-compose.yml` builds both services, waits for the backend health check before starting the frontend, and declares persistent named volumes.

## Backend container

The backend starts with:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The container health check requests `http://127.0.0.1:8000/api/health`.

Runtime variables:

| Variable | Required | Purpose |
|---|---|---|
| `GROQ_API_KEY` | Yes | Groq inference credential |
| `JWT_SECRET_KEY` | Yes | JWT signing secret |
| `FRONTEND_ORIGINS` | In deployed cross-origin use | Comma-separated CORS allowlist |

## Frontend container

The frontend Dockerfile has two stages:

1. Node 22 Alpine installs exact dependencies with `npm ci` and runs `npm run build`.
2. Nginx serves `/usr/share/nginx/html` and proxies `/api/` traffic to the Compose backend service at `http://backend:8000`.

Nginx disables proxy buffering and uses a long read timeout for SSE traffic.

## Local Compose commands

```powershell
# Build and start the full application
docker compose up --build -d

# Check container state
docker compose ps

# Inspect logs
docker compose logs --tail=100 backend frontend

# Test API through the frontend Nginx proxy
Invoke-RestMethod http://localhost:8080/api/health

# Stop containers without removing data volumes
docker compose down
```

The backend container is reachable internally by Compose DNS name `backend` on port 8000. The browser reaches the frontend through `http://localhost:8080`.

## Local persistent volumes

The Compose file defines:

| Volume | Mount path |
|---|---|
| `agentic_shopping_db` | `/app/Database` |
| `agentic_shopping_logs` | `/app/app/logs` |

Do not run `docker compose down -v` unless you intentionally want to remove the volumes. The developer verified local database persistence by removing and recreating the backend container with the same named volume and comparing table row counts.

## Railway backend deployment

The backend was deployed to Railway using the repository's backend Dockerfile. The reported public health endpoint was:

`https://agentic-shopping-assistant-production-9086b3bd.up.railway.app/api/health`

Required Railway variables:

```text
GROQ_API_KEY=<secret>
JWT_SECRET_KEY=<new strong secret>
FRONTEND_ORIGINS=https://<actual-pages-project>.pages.dev
```

Do not place secret values in GitHub or in the frontend's Vite environment.

### Persistent storage check

Before relying on hosted user accounts, favorites, or preferences, attach a Railway persistent volume at:

```text
/app/Database
```

Then create a controlled test account/preference, redeploy or restart the service, and verify the record remains. Local Docker persistence does not prove Railway persistence. Also establish a backup/export process for the SQLite file.

## Cloudflare Pages frontend deployment

Use the Git-connected Pages project with these settings:

| Setting | Value |
|---|---|
| Production branch | `main` |
| Root directory | `frontend` |
| Framework preset | React (Vite), if offered |
| Build command | `npm run build` |
| Build output directory | `dist` |
| Node version | `22` |

Set the following Pages build variable for Production:

```text
VITE_API_BASE_URL=https://agentic-shopping-assistant-production-9086b3bd.up.railway.app
```

`VITE_API_BASE_URL` is compiled into browser JavaScript and is not a secret. Never place Groq keys or JWT signing secrets in a `VITE_` variable.

After Pages creates the `pages.dev` hostname, set Railway's `FRONTEND_ORIGINS` to that exact origin, then redeploy the backend.

## Post-deployment acceptance checks

1. Open the Cloudflare Pages URL and confirm the SPA loads.
2. Register a new synthetic test user.
3. Log in and confirm token verification succeeds.
4. Search products and compare products.
5. Test product detail lookup and favorites separately.
6. Confirm SSE events arrive incrementally and the final response is rendered.
7. Inspect Railway logs for errors and Nginx/Pages network errors in the browser developer tools.
8. Verify a user preference persists across a new conversation.
9. Verify the Railway volume preserves data across an application redeploy.

## Cost and availability note

Railway free/trial allowances can change and may impose usage, sleep, or storage constraints. Treat the hosted setup as a portfolio/demo environment unless a suitable paid or otherwise durable hosting plan is selected. Confirm current provider plan limits in the provider dashboards before relying on the service for ongoing availability.
