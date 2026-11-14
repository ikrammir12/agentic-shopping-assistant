import sqlite3
from contextlib import closing

from database.connection import get_readonly_connection


with closing(get_readonly_connection()) as conn:

    # Test reading
    result = conn.execute(
        "SELECT COUNT(*) AS total FROM products"
    ).fetchone()

    print("Product count:", result["total"])

    # Test writing
    try:
        conn.execute(
            "UPDATE products SET price = price WHERE id = 1"
        )

    except sqlite3.OperationalError as error:
        print("Write blocked:", error)

    else:
        raise AssertionError(
            "Read-only connection allowed a write!"
        )