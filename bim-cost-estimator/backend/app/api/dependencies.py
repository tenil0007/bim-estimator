"""
API Dependencies
-----------------
Shared dependencies injected into endpoint functions.
"""

from fastapi import Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.config import get_settings, Settings


def get_database():
    """Database session dependency."""
    return Depends(get_db)


def get_app_settings():
    """Settings dependency."""
    return Depends(get_settings)
