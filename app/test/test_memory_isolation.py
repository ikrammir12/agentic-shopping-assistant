from contextlib import closing

from database.memory import (
    save_preference,
    get_customer_preferences
)
from database.connection import get_connection


USER_1 = "security-test-user-001"
USER_2 = "security-test-user-002"

try:
    # Insert separate customer preferences
    save_preference(USER_1, "budget", 20)
    save_preference(USER_2, "budget", 100)

    # Retrieve both customers' preferences
    preferences_1 = get_customer_preferences(USER_1)
    preferences_2 = get_customer_preferences(USER_2)

    print("Customer 1:", preferences_1)
    print("Customer 2:", preferences_2)

    # Verify isolation
    assert preferences_1["budget"] == "20"
    assert preferences_2["budget"] == "100"

    print("\nCustomer data isolation: PASSED")

finally:
    # Remove test records
    with closing(get_connection()) as conn:
        conn.execute(
            """
            DELETE FROM customer_preferences
            WHERE user_id IN (?, ?)
            """,
            (USER_1, USER_2)
        )
        conn.commit()