
from app.database.connection import get_connection
from app.services.auth_service import (
    authenticate_user,
    InvalidCredentialsError
)

EMAIL = "test-97af8921@example.com"
PASSWORD = "StrongDemoPass123!"


def test_inactive_account():

    # Temporarily deactivate the test account
    conn = get_connection()
    try:
        result = conn.execute(
            "UPDATE users SET is_active = 0 WHERE email = ?",
            (EMAIL,)
        )
        assert result.rowcount == 1, "Test account not found"
        conn.commit()
    finally:
        conn.close()

    try:
        try:
            authenticate_user(EMAIL, PASSWORD)
            raise AssertionError("Inactive account was accepted")

        except InvalidCredentialsError:
            print("PASSED: Inactive account rejected")

    finally:
        # Restore account status, even if the test fails
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE users SET is_active = 1 WHERE email = ?",
                (EMAIL,)
            )
            conn.commit()
        finally:
            conn.close()


if __name__ == "__main__":
    test_inactive_account()
