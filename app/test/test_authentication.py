
from app.services.auth_service import (
    authenticate_user,
    InvalidCredentialsError
)


def test_unknown_email():

    try:
        authenticate_user(
            "missing@example.com",
            "SomePassword123!"
        )

        raise AssertionError("Unknown account was accepted")

    except InvalidCredentialsError:
        print("PASSED: Unknown email rejected")


def test_wrong_password():

    try:
        authenticate_user(
            "test-97af8921@example.com",
            "WrongPassword123!"
        )

        raise AssertionError("Incorrect password was accepted")

    except InvalidCredentialsError:
        print("PASSED: Incorrect password rejected")


if __name__ == "__main__":
    test_unknown_email()
    test_wrong_password()
