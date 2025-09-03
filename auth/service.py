"""
Core authentication logic.

This module handles validation of credentials.
Currently uses an in-memory user store, but can be
extended to check against a database or external provider.
"""

from fastapi import HTTPException, status
from .config import USERS
from .utils import hash_password


def authenticate_user(username: str, password: str) -> str:
    """
    Authenticate a user by validating their username and password.

    Args:
        username (str): The username provided by the client.
        password (str): The password provided by the client.

    Returns:
        str: The authenticated username.

    Raises:
        HTTPException: If authentication fails (401 Unauthorized).
    """
    stored_password = USERS.get(username)

    if stored_password is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Allow both plain-text (demo) and hashed password comparison
    if stored_password == password or stored_password == hash_password(password):
        return username

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid password",
        headers={"WWW-Authenticate": "Basic"},
    )
