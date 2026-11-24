
import json
import sqlite3

from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime

from ..database.connection import get_readonly_connection
from ..database.favorites import (
    add_favorite,
    get_favorites,
    remove_favorite
)


def get_authenticated_user_id(runtime: ToolRuntime) -> str:
    """Get the authenticated user ID from graph configuration."""

    configurable = runtime.config.get("configurable", {})
    user_id = configurable.get("user_id")

    if not user_id:
        raise ValueError("Authenticated user ID is missing.")

    return user_id


def find_product(product_name: str):

    with get_readonly_connection() as conn:

        return conn.execute(
            """
            SELECT id, name
            FROM products
            WHERE name = ? COLLATE NOCASE
            """,
            (product_name.strip(),)
        ).fetchone()


@tool
def save_favorite_tool(
    product_name: str,
    runtime: ToolRuntime
) -> str:
    """Save a product to the authenticated customer's favorites.

    Use this when the customer explicitly asks to save a product.
    """

    try:
        user_id = get_authenticated_user_id(runtime)

        product = find_product(product_name)

        if product is None:
            return f"Product '{product_name}' was not found."

        added = add_favorite(
            user_id,
            product["id"]
        )

        if not added:
            return f"{product['name']} is already in your favorites."

        return f"{product['name']} was added to your favorites."

    except (ValueError, sqlite3.Error):
        return "Unable to save this favorite right now."


@tool
def get_favorites_tool(runtime: ToolRuntime) -> str:
    """Retrieve all products saved in the authenticated customer's favorites."""

    try:
        user_id = get_authenticated_user_id(runtime)

        favorites = get_favorites(user_id)

        if not favorites:
            return "You don't have any saved favorites yet."

        return json.dumps(favorites, indent=2)

    except (ValueError, sqlite3.Error):
        return "Unable to retrieve your favorites right now."


@tool
def remove_favorite_tool(
    product_name: str,
    runtime: ToolRuntime
) -> str:
    """Remove a product from the authenticated customer's favorites."""

    try:
        user_id = get_authenticated_user_id(runtime)

        product = find_product(product_name)

        if product is None:
            return f"Product '{product_name}' was not found."

        removed = remove_favorite(
            user_id,
            product["id"]
        )

        if not removed:
            return f"{product['name']} is not in your favorites."

        return f"{product['name']} was removed from your favorites."

    except (ValueError, sqlite3.Error):
        return "Unable to remove this favorite right now."
