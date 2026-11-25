# Agent Design and Tool Reference

## Model configuration

The LLM factory uses `ChatGroq` with the following source-configured settings:

| Setting | Value |
|---|---|
| Model | `openai/gpt-oss-20b` |
| Temperature | `0.7` |
| Maximum output tokens | `1020` |
| Reasoning effort | `low` |
| Retries | `2` |
| Credential | `GROQ_API_KEY` environment variable |

The key is read at runtime. It must not be committed to source control.

## Registered tools

The graph registers six tools.

### Product tools

| Tool | Purpose | Data behavior |
|---|---|---|
| `check_product_tool` | Look up one named product | Selects a product by exact name and returns basic product details or a not-found message. |
| `search_product_tool` | Search products in a category | Supports optional maximum price, organic-only filtering, and sorting. Joins review aggregates to return average rating and review count. |
| `compare_product_tool` | Compare two named products | Compares price and review-derived rating information and returns comparison results. |

Search sorting options implemented in the product tool are:

- `price_asc`
- `price_desc`
- `name`
- `rating_desc`

Search inputs are validated: category must be non-empty, maximum price must be numeric, finite, and positive when provided, and sort mode must be one of the supported values. SQL query values are passed as parameters. Sort expressions are selected from a fixed allowlist.

### Favorites tools

| Tool | Purpose |
|---|---|
| `save_favorite_tool` | Find a product and save it for the authenticated user. |
| `get_favorites_tool` | Retrieve the authenticated user's saved products. |
| `remove_favorite_tool` | Find a product and remove that user's favorite record. |

Favorite tools obtain the user ID from LangGraph runtime configuration. They do not accept a user ID supplied by the natural-language request. The favorites table has a unique constraint on `(user_id, product_id)` so the same product is not duplicated for one user.

## System behavior and boundaries

The system prompt directs the assistant to:

- Use tools for actual product information.
- Avoid inventing prices, ratings, or product details.
- Apply saved preferences when relevant, while prioritizing the latest explicit user request.
- Use favorite tools only when the user explicitly requests a favorite action.
- Never say a favorite was added or removed unless the relevant tool confirms it.
- Avoid automatically saving a product because it was merely searched or discussed.
- Avoid claiming unsupported capabilities.

The prompt also states that the assistant cannot add products to carts, place orders, or make purchases. An `orders` table in the SQLite sample database does not mean ordering is an implemented agent capability.

## Tool selection limitation

The latest reported regression run exposed inconsistent selection for product details. For case `PD-001` ("Tell me the details of Organic Manuka Honey"), the expected tool was `check_product_tool`, but the actual selected tool was `search_product_tool`. Keep this case as a regression test and improve tool descriptions/routing guidance in a later iteration. Do not hide the failure by changing the expected tool merely to obtain a green result.
