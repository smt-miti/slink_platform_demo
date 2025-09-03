"""
Pydantic schemas for request/response models in the auth module.
"""

from pydantic import BaseModel


class UserLogin(BaseModel):
    """Schema for login request payload."""
    username: str
    password: str


class UserOut(BaseModel):
    """Schema for responses containing user info."""
    username: str
    message: str
