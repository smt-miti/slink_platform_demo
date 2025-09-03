"""
FastAPI dependency functions for authentication.

These can be used in routes with Depends() to protect endpoints.
"""

from fastapi import Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from .service import authenticate_user

# HTTP Basic authentication scheme
security = HTTPBasic()


def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Dependency that retrieves and validates the current user.

    Args:
        credentials (HTTPBasicCredentials): Automatically provided by FastAPI.

    Returns:
        str: The authenticated username.
    """
    return authenticate_user(credentials.username, credentials.password)
