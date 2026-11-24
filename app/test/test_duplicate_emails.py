from app.services.auth_service import (
    register_user,
    DuplicateEmailError
)


def test_duplicate_email():

    existing_email = "test-97af8921@example.com"

    try:
        register_user(
            existing_email,
            "AnotherPassword123!"
        )

        raise AssertionError(
            "Duplicate email registration was allowed!"
        )

    except DuplicateEmailError as error:
        print("TEST PASSED")
        print("Duplicate email correctly rejected:", error)


if __name__ == "__main__":
    test_duplicate_email()