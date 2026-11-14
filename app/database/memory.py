import os
from contextlib import closing

from .connection import get_connection


def create_memory_table():
    """Create the customer preferences table."""

    with closing(get_connection()) as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS customer_preferences (

                user_id TEXT NOT NULL,

                preference_key TEXT NOT NULL,

                preference_value TEXT NOT NULL,

                updated_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                PRIMARY KEY (user_id, preference_key)
            )
        """)

        conn.commit()


def save_preference(
    user_id: str,
    preference_key: str,
    preference_value: str | int | float | bool
):
    """Save a new preference or update an existing preference."""

    user_id = user_id.strip()
    preference_key = preference_key.strip().lower()
    preference_value = str(preference_value).strip()

    if not user_id:
        raise ValueError("user_id cannot be empty.")

    if not preference_key:
        raise ValueError("preference_key cannot be empty.")

    if not preference_value:
        raise ValueError("preference_value cannot be empty.")

    with closing(get_connection()) as conn:

        conn.execute("""
            INSERT INTO customer_preferences
            (user_id, preference_key, preference_value)

            VALUES (?, ?, ?)

            ON CONFLICT(user_id, preference_key)

            DO UPDATE SET
                preference_value = excluded.preference_value,
                updated_at = CURRENT_TIMESTAMP

        """, (
            user_id,
            preference_key,
            preference_value
        ))

        conn.commit()

    print(f"Saved preference: {preference_key} = {preference_value}")



def get_customer_preferences(user_id: str) -> dict[str, str]:
    """Retrieve all saved preferences for a customer."""

    user_id = user_id.strip()

    if not user_id:
        raise ValueError("user_id cannot be empty.")

    with closing(get_connection()) as conn:

        rows = conn.execute("""
            SELECT preference_key, preference_value

            FROM customer_preferences

            WHERE user_id = ?

            ORDER BY preference_key

        """, (user_id,)).fetchall()

    preferences = {
        row["preference_key"]: row["preference_value"]
        for row in rows
    }

    return preferences

if __name__ == "__main__":

    # Create the table
    create_memory_table()

    # Save customer preferences
    save_preference(
        "demo-customer-001",
        "budget",
        15
    )

    save_preference(
        "demo-customer-001",
        "category",
        "honey"
    )

    save_preference(
        "demo-customer-001",
        "sort_by",
        "rating_desc"
    )

    print("\nFIRST RETRIEVAL:")

    preferences = get_customer_preferences(
        "demo-customer-001"
    )

    print(preferences)

    # Update the budget
    save_preference(
        "demo-customer-001",
        "budget",
        20
    )

    print("\nAFTER UPDATING BUDGET:")

    preferences = get_customer_preferences(
        "demo-customer-001"
    )

    print(preferences)
