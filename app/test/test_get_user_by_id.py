from app.database.auth import get_user_by_id


def test_existing_user():

    user = get_user_by_id(
        "53912ac3-3b82-479e-8869-9332586d6a2f"
    )

    assert user is not None
    assert user["user_id"] == "53912ac3-3b82-479e-8869-9332586d6a2f"
    assert "email" in user
    assert "is_active" in user

    print("Existing user lookup passed!")


def test_missing_user():

    user = get_user_by_id("non-existing-user")

    assert user is None

    print("Missing user lookup passed!")


if __name__ == "__main__":
    test_existing_user()
    test_missing_user()