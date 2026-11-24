
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv


# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


# JWT configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is missing from .env")

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# Generate JWT access token
def create_access_token(user_id: str) -> str:

    # Current UTC time
    now = datetime.now(timezone.utc)

    # Token expiration time
    expires_at = now + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    # JWT payload
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": expires_at
    }

    # Sign and generate token
    token = jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )

    return token


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(
        token,
        JWT_SECRET_KEY,
        algorithms=[JWT_ALGORITHM],
        options={
            "require": ["sub", "exp", "iat"]
        }
    )

    user_id = payload.get("sub")

    if not isinstance(user_id, str) or not user_id.strip():
        raise jwt.InvalidTokenError("Invalid token subject")

    return payload