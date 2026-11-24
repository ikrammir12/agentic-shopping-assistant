
from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()


# Generate a secure password hash
def hash_password(password: str) -> str:
    password_hash = password_hasher.hash(password)
    return password_hash


# Verify a password against its stored hash
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hasher.verify(plain_password, hashed_password)
