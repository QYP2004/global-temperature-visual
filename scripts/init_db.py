"""Initialize the SQLite schema.

Usage:
    python -m scripts.init_db
"""
from backend.database import init_db


if __name__ == "__main__":
    init_db()
    print("Database schema initialized.")
