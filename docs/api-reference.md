# API Reference

Base path: `/api`

Protected endpoints use an HTTP Bearer JWT in the `Authorization` header.

## Health

### `GET /api/health`

No authentication required.

Example response:

```json
{
  "status": "ok",
  "application": "agentic_shopping_assistant"
}
```

## Authentication

### `POST /api/auth/register`

Creates a user account.

Request:

```json
{
  "email": "person@example.com",
  "password": "a-long-password"
}
```

The password schema has a minimum length of 12 and maximum length of 128. The service normalizes email to lowercase, generates a UUID user ID, hashes the password, and stores the account. Success returns HTTP 201. A duplicate email returns HTTP 409.

### `POST /api/auth/login`

Request:

```json
{
  "email": "person@example.com",
  "password": "a-long-password"
}
```

Success returns an access token, token type (`bearer`), and safe user details. Invalid credentials return HTTP 401. The JWT is signed with HS256 and expires after 30 minutes.

### `GET /api/auth/verify`

Requires `Authorization: Bearer <token>`.

Successful response:

```json
{
  "authenticated": true,
  "user_id": "<user-uuid>"
}
```

The dependency verifies the token and checks that the corresponding account still exists and is active.

## Chat

### `POST /api/chat`

Requires bearer authentication.

Request:

```json
{
  "message": "Find organic honey under $20",
  "conversation_id": "conversation-123"
}
```

The API invokes the LangGraph workflow using a thread ID scoped as `{user_id}:{conversation_id}`.

Response shape:

```json
{
  "conversation_id": "conversation-123",
  "answer": "...",
  "products": []
}
```

The `products` array is extracted from `search_product_tool` messages and deduplicated by product ID.

### `POST /api/chat/stream`

Requires bearer authentication. Accepts the same request shape as `/api/chat` and returns `text/event-stream`.

The event stream contains named events such as `request_start`, `graph_start`, `llm_start`, `llm_end`, `tool_call`, `tool_start`, `tool_end`, `final`, and `error`. Event data is JSON. The frontend parses events incrementally and associates them with the active response.

The final event includes the conversation ID, graph run ID, answer, and collected product results.

## CORS configuration

FastAPI reads `FRONTEND_ORIGINS` as a comma-separated list of allowed origins. Origins are trimmed and trailing slashes removed. If unset, the application defaults to local Vite origins:

- `http://localhost:5173`
- `http://127.0.0.1:5173`

Set the exact deployed Cloudflare Pages origin in Railway, for example `https://<project>.pages.dev`. Do not include a path or trailing slash.

## API notes

- Chat endpoints are authenticated.
- Registration and login are public endpoints.
- No order placement or checkout endpoint is implemented in the inspected API.
- The health endpoint confirms process/API availability; it does not by itself prove LLM connectivity or full agent correctness.
