from app.security import (
    create_access_token,
    decode_access_token
)


def test_valid_token():

    user_id = "test-user-123"

    token = create_access_token(user_id)

    payload = decode_access_token(token)

    assert payload["sub"] == user_id
    assert "exp" in payload
    assert "iat" in payload

    print("Valid JWT verification passed!")

import jwt


def test_tampered_token():

    token = create_access_token("test-user-123")

    parts = token.split(".")

    # Change the payload segment
    first_char = parts[1][0]
    replacement = "A" if first_char != "A" else "B"

    parts[1] = replacement + parts[1][1:]

    tampered_token = ".".join(parts)

    try:
        decode_access_token(tampered_token)

    except jwt.InvalidTokenError:
        print("Tampered JWT rejected successfully!")

    else:
        raise AssertionError("Tampered token was accepted!")


if __name__ == "__main__":
    test_valid_token()
    test_tampered_token()