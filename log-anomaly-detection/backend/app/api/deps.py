"""
deps.py

Shared FastAPI dependencies for the api/routes/ modules. Kept as a single
import surface  so routes never reach into
app.db.database directly - if the session-management strategy ever changes,
only this file needs to change.
"""

from app.db.database import get_db

__all__ = ["get_db"]