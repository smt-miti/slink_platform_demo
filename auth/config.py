"""
Configuration for the auth module.

This defines how users are loaded. For demo purposes,
this uses an in-memory dictionary. 
In production, this can be extended to load users from a database or external service.
"""

from typing import Dict
import os

# Demo in-memory user store (username → password)
# Replace with DB-backed logic in production.
USERS: Dict[str, str] = {
    "slink_demo": os.getenv("DEMO_USER_PASSWORD", "slink_demo"),
    "slink_admin": os.getenv("ADMIN_USER_PASSWORD", "slink_admin"),
}
