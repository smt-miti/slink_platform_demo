"""
Utility functions for the auth module.
"""

import hashlib


def hash_password(password: str) -> str:
    """
    Return a SHA256 hash of the given password.

    Note:
        This is only for demo purposes.
        In production, use a strong hashing library such as passlib[bcrypt].
    """
    return hashlib.sha256(password.encode()).hexdigest()
