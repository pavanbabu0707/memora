import os
import sqlite3
from contextlib import closing
from pathlib import Path


def get_database_path() -> Path:
    configured_path = os.getenv("MEMORA_DATABASE_PATH")
    if configured_path:
        return Path(configured_path)

    return Path(__file__).resolve().parents[1] / "data" / "memora.db"


def save_photo_metadata(
    *,
    photo_id: str,
    original_filename: str,
    stored_filename: str,
    stored_path: Path,
    file_size: int,
    uploaded_at: str,
) -> None:
    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS photos (
                id TEXT PRIMARY KEY,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                uploaded_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO photos (
                id,
                original_filename,
                stored_filename,
                stored_path,
                file_size,
                uploaded_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                photo_id,
                original_filename,
                stored_filename,
                str(stored_path),
                file_size,
                uploaded_at,
            ),
        )
        connection.commit()
