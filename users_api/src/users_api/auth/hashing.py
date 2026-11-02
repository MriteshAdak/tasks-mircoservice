"""Password hashing isolated from routes and persistence code."""

from pwdlib import PasswordHash


_password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Return a non-reversible password hash for storage."""

    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a candidate password against its stored hash."""

    return _password_hash.verify(password, password_hash)
