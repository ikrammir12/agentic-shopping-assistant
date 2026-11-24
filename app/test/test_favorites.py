
from app.database.favorites import (
    add_favorite,
    get_favorites,
    remove_favorite
)

# Replace with an existing user ID from your database.
USER_ID = "53912ac3-3b82-479e-8869-9332586d6a2f"

# Product ID from your products table.
PRODUCT_ID = 1


def test_favorites():

    print("\n1. Adding favorite...")

    result = add_favorite(USER_ID, PRODUCT_ID)
    print("Added:", result)

    print("\n2. Retrieving favorites...")

    favorites = get_favorites(USER_ID)
    print(favorites)

    print("\n3. Removing favorite...")

    result = remove_favorite(USER_ID, PRODUCT_ID)
    print("Removed:", result)

    print("\n4. Checking after removal...")

    favorites = get_favorites(USER_ID)
    print(favorites)


if __name__ == "__main__":
    test_favorites()
