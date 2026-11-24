import sqlite3

from .connection import get_connection


def create_favorites_table():

    with get_connection() as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS favorites (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id TEXT NOT NULL,

                product_id INTEGER NOT NULL,

                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE,

                FOREIGN KEY (product_id)
                    REFERENCES products(id)
                    ON DELETE CASCADE,

                UNIQUE(user_id, product_id)
            )
        """)

        conn.commit()



def add_favorite(user_id: str, product_id: int) -> bool:
    """Save a product to a user's favorites."""

    with get_connection() as conn:

        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO favorites
                (user_id, product_id)
            VALUES (?, ?)
            """,
            (user_id, product_id)
        )

        conn.commit()

        return cursor.rowcount > 0


def get_favorites(user_id: str) -> list[dict]:
    """Retrieve all products saved by a user."""

    with get_connection() as conn:

        rows = conn.execute(
            """
            SELECT
                p.id,
                p.name,
                p.category,
                p.price,
                p.description,
                f.created_at

            FROM favorites AS f

            JOIN products AS p
                ON f.product_id = p.id

            WHERE f.user_id = ?

            ORDER BY f.created_at DESC
            """,
            (user_id,)
        ).fetchall()

        return [dict(row) for row in rows]


def remove_favorite(user_id: str, product_id: int) -> bool:
    """Remove a product from a user's favorites."""

    with get_connection() as conn:

        cursor = conn.execute(
            """
            DELETE FROM favorites
            WHERE user_id = ? AND product_id = ?
            """,
            (user_id, product_id)
        )

        conn.commit()

        return cursor.rowcount > 0
