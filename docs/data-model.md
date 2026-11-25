# Database and Persistence

The application uses SQLite. The database file path is resolved by `app/database/connection.py` as:

```text
<Project root>/Database/store.db
```

Within the backend Docker image, this corresponds to `/app/Database/store.db`.

The connection helper provides a normal connection and a read-only connection. Rows are exposed through `sqlite3.Row`, allowing dictionary-like access. Foreign-key enforcement is enabled on writable connections.

## Tables in the inspected sample database

The uploaded sample database contained the following tables and row counts at inspection time. Counts are snapshots of that uploaded file, not guaranteed values for future copies.

| Table | Rows in uploaded sample | Purpose |
|---|---:|---|
| `products` | 32 | Product catalog |
| `reviews` | 102 | Product ratings and review text |
| `orders` | 0 | Order-shaped schema; no order placement feature is exposed by the current agent API |
| `customer_preferences` | 105 | User-scoped reusable preferences |
| `users` | 8 | User accounts |
| `favorites` | 0 | User-saved products |

## Table definitions

### `products`

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER | Primary key |
| `name` | TEXT | Required product name |
| `category` | TEXT | Product category |
| `price` | REAL | Product price |
| `description` | TEXT | Product description |
| `is_organic` | INTEGER | Defaults to 0; used by organic-only search |

### `reviews`

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER | Autoincrement primary key |
| `product_id` | INTEGER | References `products.id` |
| `rating` | REAL | Used for average rating aggregation |
| `reviewer_name` | TEXT | Reviewer display name |
| `review_text` | TEXT | Review content |

The search tool aggregates `AVG(rating)` and `COUNT(rating)` per product and joins the result to products.

### `users`

| Column | Type | Notes |
|---|---|---|
| `user_id` | TEXT | Primary key |
| `email` | TEXT | Required and unique |
| `password_hash` | TEXT | Hashed password, never plaintext |
| `is_active` | INTEGER | Defaults to 1 |
| `created_at` | TEXT | Defaults to current timestamp |

### `customer_preferences`

| Column | Type | Notes |
|---|---|---|
| `user_id` | TEXT | User key |
| `preference_key` | TEXT | Preference type |
| `preference_value` | TEXT | Stored value |
| `updated_at` | TEXT | Defaults to current timestamp |

The primary key is `(user_id, preference_key)`. Saving an existing key updates its value and timestamp.

### `favorites`

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER | Autoincrement primary key |
| `user_id` | TEXT | References `users.user_id`, cascade delete |
| `product_id` | INTEGER | References `products.id`, cascade delete |
| `created_at` | TEXT | Defaults to current timestamp |

A unique constraint on `(user_id, product_id)` prevents duplicate favorites for the same user/product pair.

### `orders`

The uploaded schema contains `id`, `product_id`, `product_name`, `price`, and `ordered_at`. The current agent prompt and API do not implement ordering or purchase flows. Treat this table as schema/demo data only unless a future feature implements its lifecycle.

## Persistence behavior

### Local Docker Compose

The Compose file declares named volumes:

- `agentic_shopping_db` mounted at `/app/Database`
- `agentic_shopping_logs` mounted at `/app/app/logs`

The local database persistence test performed during development compared row counts before and after container recreation. Both copies reported: products 32, reviews 102, orders 0, customer_preferences 105, users 8, favorites 0.

### Hosted Railway deployment

A persistent Railway volume must be attached at `/app/Database` to preserve SQLite data across deployments/restarts. Confirm this is configured and test it separately. Do not assume local Compose volumes automatically exist on Railway.

## Sample data and privacy

The project uses synthetic demonstration data according to the developer. Before publishing `Database/store.db`, verify that all emails, password hashes, preference rows, and any names are synthetic and not associated with real people or reused credentials. Never publish real `.env` files or secrets.
