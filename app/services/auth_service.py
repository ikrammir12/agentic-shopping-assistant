
import uuid

from ..passwords import hash_password
from ..database.auth import create_user
from ..database.auth import get_user_by_email
from ..passwords import verify_password
from ..security import create_access_token
import sqlite3

class DuplicateEmailError(Exception):
    pass

#We need this class to show the invalide crendital 
class InvalidCredentialsError(Exception):
    pass


def register_user(email: str, password: str) -> dict:

    # 1. Normalize email
    normalized_email = email.strip().lower()

    # 2. Generate unique user ID
    user_id = str(uuid.uuid4())

    # 3. Hash the password
    password_hash = hash_password(password)

    try:
        # 4. Save the user in SQLite
        create_user(
            user_id,
            normalized_email,
            password_hash
        )
    except sqlite3.IntegrityError as exc:
        raise DuplicateEmailError(
            "An account with this email already exists."
        ) from exc
         
    # 5. Return safe user information
    return {
        "user_id": user_id,
        "email": normalized_email
    }


def authenticate_user(email: str, password: str) -> dict:

    # 1. Normalize email
    normalized_email = email.strip().lower()

    # 2. Retrieve account from database
    account = get_user_by_email(normalized_email)

    # 3. Check whether account exists
    if account is None:
        raise InvalidCredentialsError(
            "Invalid email or password."
        )

    # 4. Verify submitted password
    password_valid = verify_password(
        password,
        account["password_hash"]
    )

    if not password_valid:
        raise InvalidCredentialsError(
            "Invalid email or password."
        )

    # 5. Check account status
    if account["is_active"] != 1:
        raise InvalidCredentialsError(
            "Invalid email or password."
        )

    # 6. Return safe customer information
    return {
        "user_id": account["user_id"],
        "email": account["email"]
    }


def login_user(email: str, password: str) -> dict:

    # 1. Authenticate customer
    auth_user = authenticate_user(email, password)

    # 2. Extract user ID
    user_id = auth_user["user_id"]

    # 3. Generate JWT access token
    access_token = create_access_token(user_id)

    # 4. Return login response
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": auth_user
    }