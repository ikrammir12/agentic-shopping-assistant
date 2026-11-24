#This is product tool ,here we will add 3 tools ,
#1=check_product_tool => this tools shows the specific product details by product name
#2=search_product_tool => this tools search products for specific category
#3=compare_product_tools => This tool will compare the two functions 

from langchain.tools import tool
from contextlib import closing
from ..database.connection import get_readonly_connection
import math
import sqlite3
import time
from ..logging_config import logger, traced


@tool
@traced("tool.check_product")
def check_product_tool(product_name: str):
    """Check specific product details by product name."""

    start_time = time.perf_counter()

    logger.info(
        "Product check started | product_name=%s",
        product_name
    )

    try:
        with closing(get_readonly_connection()) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM products WHERE name=?",
                (product_name,)
            )

            result = cursor.fetchone()

        if result:
            response = (
                f"Product Name: {result['name']}, "
                f"Price: {result['price']}, "
                f"Category: {result['category']}"
            )
        else:
            response = "product not found"

        duration = time.perf_counter() - start_time

        logger.info(
            "Product check completed | duration_seconds=%.3f | found=%s",
            duration,
            result is not None
        )

        return response

    except sqlite3.Error:
        duration = time.perf_counter() - start_time

        logger.exception(
            "Database error while checking product | "
            "duration_seconds=%.3f | product_name=%s",
            duration,
            product_name
        )
        raise

def validate_search_input(category, max_price, sort_by):
    # Validate category
    if not isinstance(category, str) or not category.strip():
        raise ValueError("Category must be a non-empty string.")

    # Validate maximum price
    if max_price is not None:
        if isinstance(max_price, bool) or not isinstance(max_price, (int, float)):
            raise ValueError("Budget must be numeric.")

        if not math.isfinite(max_price):
            raise ValueError("Budget must be a finite number.")

        if max_price <= 0:
            raise ValueError("Budget must be positive.")

    # Validate sorting option
    allowed_sort_options = {"price_asc", "price_desc", "name", "rating_desc"}

    if not isinstance(sort_by, str):
        raise ValueError("Sorting option must be a string.")

    sort_by = sort_by.strip().lower()

    if sort_by not in allowed_sort_options:
        raise ValueError("Invalid sorting option.")

    return category.strip().lower(), max_price, sort_by



@tool
@traced("tool.search_product")
def search_product_tool(
    category: str,
    max_price: float | None = None,
    sort_by: str = "price_asc",
    organic_only: bool = False
) -> list | str:
    """
    Search products by category with optional maximum price
    and organic-only filtering.

    Also returns average customer rating and review count
    calculated from the reviews database.

    Sort results by price ascending, price descending, product name,
    or average customer rating descending.
    """

    # Step 1: Validate inputs
    category, max_price, sort_by = validate_search_input(
        category,
        max_price,
        sort_by
    )

    logger.info(
        "Product search started | category=%s | max_price=%s "
        "| sort_by=%s | organic_only=%s",
        category,
        max_price,
        sort_by,
        organic_only
    )

    # Step 2: Base SQL query with review aggregation
    query = """
        SELECT
            p.id,
            p.name,
            p.category,
            p.description,
            p.price,
            p.is_organic,

            r.average_rating,
            COALESCE(r.review_count, 0) AS review_count

        FROM products p

        LEFT JOIN (
            SELECT
                product_id,
                ROUND(AVG(rating), 2) AS average_rating,
                COUNT(rating) AS review_count
            FROM reviews
            GROUP BY product_id
        ) r ON p.id = r.product_id

        WHERE p.category = ?
    """

    parameters = [category]

    # Step 3: Apply optional budget filter
    if max_price is not None:
        query += " AND p.price <= ?"
        parameters.append(max_price)

    # Step 4: Apply organic-only filter
    if organic_only:
        query += " AND p.is_organic = ?"
        parameters.append(1)

    # Step 5: Apply sorting
    sort_options = {
        "price_asc": "p.price ASC",
        "price_desc": "p.price DESC",
        "name": "p.name COLLATE NOCASE ASC",
        # Products without ratings are placed last. Ties are broken by
        # review count, then price, then name for deterministic results.
        "rating_desc": (
            "CASE WHEN r.average_rating IS NULL THEN 1 ELSE 0 END ASC, "
            "r.average_rating DESC, "
            "r.review_count DESC, "
            "p.price ASC, "
            "p.name COLLATE NOCASE ASC"
        ),
    }

    query += f" ORDER BY {sort_options[sort_by]}"

    # Step 6: Measure database execution time
    start_time = time.perf_counter()

    try:
        with closing(get_readonly_connection()) as conn:
            cursor = conn.cursor()

            cursor.execute(query, parameters)

            results = cursor.fetchall()

            products = [dict(row) for row in results]

        duration = time.perf_counter() - start_time

        logger.info(
            "Product search completed | duration_seconds=%.3f "
            "| result_count=%d | organic_only=%s",
            duration,
            len(products),
            organic_only
        )

        # An empty list can be serialized as empty tool content. Some model
        # providers reject an empty role=tool content field, preventing the
        # agent from generating a helpful no-results response. Return a
        # non-empty explanation when there are no matches.
        if not products:
            return (
                f"No products found in category '{category}' with the current "
                "filters. Explain that no matches were found and suggest "
                "relaxing the budget or product filters."
            )

        return products

    except sqlite3.Error:
        duration = time.perf_counter() - start_time

        logger.exception(
            "Database error while searching products "
            "| duration_seconds=%.3f | category=%s",
            duration,
            category
        )

        raise


@tool
@traced("tool.compare_product")
def compare_product_tool(
    product_name1: str,
    product_name2: str
) -> dict:
    """
    Compare two products using their prices, average customer ratings,
    and number of reviews. Identify the cheapest and highest-rated product
    and recommend one when the data supports a clear winner.
    """

    # Step 1: Start timing the complete comparison operation
    start_time = time.perf_counter()

    logger.info(
        "Product comparison started | product_1=%s | product_2=%s",
        product_name1,
        product_name2
    )

    try:

        # Step 2: Retrieve both products
        with closing(get_readonly_connection()) as conn:
            cursor = conn.cursor()

            def get_product_details(product_name):

                cursor.execute("""
                    SELECT
                        p.id,
                        p.name,
                        p.price,
                        AVG(r.rating) AS avg_rating,
                        COUNT(r.rating) AS review_count
                    FROM products p
                    LEFT JOIN reviews r
                        ON p.id = r.product_id
                    WHERE p.name COLLATE NOCASE = ?
                    GROUP BY p.id, p.name, p.price
                """, (product_name,))

                row = cursor.fetchone()

                return dict(row) if row else None

            product1 = get_product_details(product_name1)
            product2 = get_product_details(product_name2)

        # Step 3: Check whether products exist
        if product1 is None:
            duration = time.perf_counter() - start_time

            logger.info(
                "Product comparison completed | duration_seconds=%.3f | status=not_found",
                duration
            )

            return {"error": f"{product_name1} not found"}

        if product2 is None:
            duration = time.perf_counter() - start_time

            logger.info(
                "Product comparison completed | duration_seconds=%.3f | status=not_found",
                duration
            )

            return {"error": f"{product_name2} not found"}

        # Step 4: Extract product information
        price1 = product1["price"]
        price2 = product2["price"]

        rating1 = product1["avg_rating"]
        rating2 = product2["avg_rating"]

        # Step 5: Identify the highest-rated product
        if rating1 is None or rating2 is None:
            highest_rated = None

        elif rating1 > rating2:
            highest_rated = product1["name"]

        elif rating2 > rating1:
            highest_rated = product2["name"]

        else:
            highest_rated = "Tie"

        # Step 6: Identify the lowest-priced product
        if price1 is None or price2 is None:
            lowest_price = None

        elif price1 < price2:
            lowest_price = product1["name"]

        elif price2 < price1:
            lowest_price = product2["name"]

        else:
            lowest_price = "Tie"

        # Step 7: Determine the recommendation
        recommendation = None

        if None in (price1, price2, rating1, rating2):

            reason = "Insufficient data for a fair comparison."

        elif price1 == price2 and rating1 == rating2:

            reason = "Both products have equal prices and ratings."

        elif price1 <= price2 and rating1 >= rating2:

            recommendation = product1["name"]
            reason = "Better or equal rating with a lower or equal price."

        elif price2 <= price1 and rating2 >= rating1:

            recommendation = product2["name"]
            reason = "Better or equal rating with a lower or equal price."

        else:

            reason = "There is a trade-off between price and rating."

        # Step 8: Prepare comparison results
        comparison_result = {
            "product_1": product1,
            "product_2": product2,
            "highest_rated": highest_rated,
            "lowest_price": lowest_price,
            "recommended_product": recommendation,
            "reason": reason
        }

        # Step 9: Record successful execution duration
        duration = time.perf_counter() - start_time

        logger.info(
            "Product comparison completed | duration_seconds=%.3f | status=success",
            duration
        )

        return comparison_result

    except sqlite3.Error:
        duration = time.perf_counter() - start_time

        logger.exception(
            "Database error while comparing products | "
            "duration_seconds=%.3f | product_1=%s | product_2=%s",
            duration,
            product_name1,
            product_name2
        )

        raise

