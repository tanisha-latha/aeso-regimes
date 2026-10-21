"""Pull AESO data into a local SQLite database, incrementally."""

import os
import sqlite3
from pathlib import Path

DB_PATH = Path("data/aeso.db")


def get_api_key() -> str:
    key = os.environ.get("AESO_API_KEY")
    if not key:
        raise RuntimeError("Set AESO_API_KEY before running ingestion.")
    return key


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def init_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pool_price (
            hour_start TEXT PRIMARY KEY,
            price_cad_mwh REAL
        )
        """
    )
    conn.commit()


def main() -> None:
    get_api_key()
    conn = connect()
    init_schema(conn)
    conn.close()


if __name__ == "__main__":
    main()
