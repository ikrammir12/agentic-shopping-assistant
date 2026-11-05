import sqlite3
from pathlib import Path

# Locate the project root
BASE_DIR = Path(__file__).resolve().parents[2]

# Locate the existing database
DB_PATH = BASE_DIR / "Database" / "store.db"


def get_connection():
    """Create and return a SQLite database connection."""

    if not DB_PATH.is_file():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    conn = sqlite3.connect(str(DB_PATH))

    # Return rows as dictionary-like objects
    conn.row_factory = sqlite3.Row

    return conn