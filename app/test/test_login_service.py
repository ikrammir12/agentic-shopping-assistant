from app.services.auth_service import login_user


def test_login():

    result = login_user(
        "test-97af8921@example.com",
        "StrongDemoPass123!"
    )

    assert result["access_token"]
    assert result["token_type"] == "bearer"
    assert result["user"]["user_id"]
    assert "password_hash" not in result["user"]

    assert len(result["access_token"].split(".")) == 3

    print("LOGIN TEST PASSED")
    print("JWT generated successfully")
    print("User:", result["user"])


if __name__ == "__main__":
    test_login()