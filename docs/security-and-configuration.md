# Security and Configuration Notes

## Environment variables

| Variable | Where it belongs | Exposure |
|---|---|---|
| `GROQ_API_KEY` | Backend environment only | Secret |
| `JWT_SECRET_KEY` | Backend environment only | Secret |
| `FRONTEND_ORIGINS` | Backend environment | Configuration, not secret |
| `VITE_API_BASE_URL` | Cloudflare Pages build environment | Public API origin; embedded in browser assets |

Use `.env.example` for placeholder names and safe setup instructions. Keep `.env` and `frontend/.env` out of Git.

## Password and token handling

- Passwords are hashed using `pwdlib`'s recommended password-hashing implementation.
- JWTs use HS256 and contain `sub`, `iat`, and `exp` claims.
- Access tokens expire after 30 minutes.
- Protected API endpoints use HTTP Bearer authentication.
- The authentication dependency verifies the JWT and checks that the user still exists and has `is_active = 1`.

## User isolation

The API derives the user ID from the verified JWT, then passes it as graph configuration. Favorite tools obtain this ID from runtime configuration. The SQLite favorites and preference records are keyed by user ID. This prevents the natural-language request from selecting another user's favorite namespace.

## CORS

`FRONTEND_ORIGINS` is a comma-separated list. Set it to the exact production frontend origin. Avoid wildcard origins for a credentialed production API.

## SQL safety

The product search validates category, budget, and sorting inputs. Values are passed as SQL parameters, and sort expressions are selected from a fixed allowlist. The individual product lookup uses a parameterized name query. Favorite and preference operations are also scoped by the authenticated user ID.

## Data hygiene before publishing

The sample database inspected in the archive contains user and preference rows. The developer states the data is synthetic. Before publishing, verify that emails and password hashes are synthetic and that no real personal data or reused credentials are present. A password hash is still sensitive account data and should not be treated as harmless merely because it is not plaintext.

## Operational items to verify before calling the deployment production-ready

- A Railway persistent volume is mounted at `/app/Database`.
- A database backup and restore procedure exists.
- JWT secret rotation is documented.
- Public Pages origin is the only production CORS origin unless additional clients are intentionally supported.
- Error logs do not contain API keys, passwords, JWTs, or full authorization headers.
