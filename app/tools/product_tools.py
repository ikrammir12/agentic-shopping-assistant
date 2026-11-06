#This is product tool ,here we will add 3 tools ,
#1=check_product_tool => this tools shows the specific product details by product name
#2=search_product_tool => this tools search products for specific category
#3=compare_product_tools => This tool will compare the two functions 

from langchain.tools import tool
from contextlib import closing
from database.connection import get_connection


@tool
def check_product_tool(product_name: str):
    """ This tool check the specific product details by product name"""
    
    with closing(get_connection()) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM products WHERE name=?",(product_name,))

        result = cursor.fetchone()
        if result:
                return f"Product Name: {result['name']}, Price: {result['price']}, Category: {result['category']}"
        else:
            return "product not found"


@tool
def search_product_tool(
    category: str,
    max_price: float | None = None,
    sort_by: str = "price_asc"
) -> list:
    """
    Search products by category with an optional maximum price.
    Sort results by price ascending, descending, or product name.
    """

    # Validate sorting option
    sort_options = {
        "price_asc": "price ASC",
        "price_desc": "price DESC",
        "name": "name ASC"
    }

    if sort_by not in sort_options:
        return {"error": "Invalid sorting option."}

    query = """
        SELECT id, name, category, description, price
        FROM products
        WHERE category = ?
    """

    parameters = [category]

    # Apply optional price filter
    if max_price is not None:
        query += " AND price <= ?"
        parameters.append(max_price)

    # Apply sorting
    query += f" ORDER BY {sort_options[sort_by]}"

    with closing(get_connection()) as conn:
        cursor = conn.cursor()

        cursor.execute(query, parameters)

        results = cursor.fetchall()

        return [dict(row) for row in results]

@tool
def compare_product_tool(
    product_name1: str,
    product_name2: str
) -> dict:
    """
    Compare two products using their prices, average customer ratings,
    and number of reviews. Identify the cheapest and highest-rated product
    and recommend one when the data supports a clear winner.
    """

    with closing(get_connection()) as conn:
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
                WHERE p.name = ?
                GROUP BY p.id, p.name, p.price
            """, (product_name,))

            row = cursor.fetchone()

            return dict(row) if row else None

        product1 = get_product_details(product_name1)
        product2 = get_product_details(product_name2)

    # Check whether products exist
    if product1 is None:
        return {"error": f"{product_name1} not found"}

    if product2 is None:
        return {"error": f"{product_name2} not found"}

    # Extract product information
    price1 = product1["price"]
    price2 = product2["price"]

    rating1 = product1["avg_rating"]
    rating2 = product2["avg_rating"]

    # Identify the highest-rated product
    if rating1 is None or rating2 is None:
        highest_rated = None

    elif rating1 > rating2:
        highest_rated = product1["name"]

    elif rating2 > rating1:
        highest_rated = product2["name"]

    else:
        highest_rated = "Tie"

    # Identify the lowest-priced product
    if price1 is None or price2 is None:
        lowest_price = None

    elif price1 < price2:
        lowest_price = product1["name"]

    elif price2 < price1:
        lowest_price = product2["name"]

    else:
        lowest_price = "Tie"

    # Determine the recommendation
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

    # Return complete comparison results
    return {
        "product_1": product1,
        "product_2": product2,
        "highest_rated": highest_rated,
        "lowest_price": lowest_price,
        "recommended_product": recommendation,
        "reason": reason
    }