import sqlite3
import shutil
from collections.abc import Iterator
from contextlib import closing
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


@pytest.fixture
def temporary_directory() -> Iterator[Path]:
    directory = Path(__file__).parent / f".tmp-{uuid4()}"
    directory.mkdir()
    try:
        yield directory
    finally:
        shutil.rmtree(directory)


def configure_test_paths(
    temporary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path]:
    photo_directory = temporary_directory / "photos"
    database_path = temporary_directory / "memora.db"
    monkeypatch.setenv("MEMORA_PHOTO_STORAGE_DIR", str(photo_directory))
    monkeypatch.setenv("MEMORA_DATABASE_PATH", str(database_path))
    return photo_directory, database_path


@pytest.mark.parametrize(
    ("original_filename", "content_type", "content"),
    [
        ("vacation.jpg", "image/jpeg", b"jpg-photo"),
        ("vacation.png", "image/png", b"png-photo"),
    ],
)
def test_upload_supported_photo(
    temporary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
    original_filename: str,
    content_type: str,
    content: bytes,
) -> None:
    photo_directory, database_path = configure_test_paths(
        temporary_directory, monkeypatch
    )

    response = client.post(
        "/photos",
        files={"file": (original_filename, content, content_type)},
    )

    assert response.status_code == 200
    response_body = response.json()
    UUID(response_body["id"])
    assert response_body == {
        "id": response_body["id"],
        "original_filename": original_filename,
        "stored_filename": f"{response_body['id']}{Path(original_filename).suffix}",
    }
    stored_path = photo_directory / response_body["stored_filename"]
    assert stored_path.read_bytes() == content

    with closing(sqlite3.connect(database_path)) as connection:
        record = connection.execute(
            """
            SELECT
                id,
                original_filename,
                stored_filename,
                stored_path,
                file_size,
                uploaded_at
            FROM photos
            """
        ).fetchone()

    assert record is not None
    assert record[:5] == (
        response_body["id"],
        original_filename,
        response_body["stored_filename"],
        str(stored_path),
        len(content),
    )
    assert datetime.fromisoformat(record[5]).utcoffset().total_seconds() == 0


def test_upload_rejects_unsupported_file_type(
    temporary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    photo_directory, database_path = configure_test_paths(
        temporary_directory, monkeypatch
    )

    response = client.post(
        "/photos",
        files={"file": ("notes.txt", b"not-a-photo", "text/plain")},
    )

    assert response.status_code == 400
    assert not photo_directory.exists()
    assert not database_path.exists()


def test_separate_uploads_create_separate_database_records(
    temporary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, database_path = configure_test_paths(temporary_directory, monkeypatch)

    first_response = client.post(
        "/photos",
        files={"file": ("first.jpg", b"first-photo", "image/jpeg")},
    )
    second_response = client.post(
        "/photos",
        files={"file": ("second.png", b"second-photo", "image/png")},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    with closing(sqlite3.connect(database_path)) as connection:
        records = connection.execute(
            "SELECT id, original_filename FROM photos ORDER BY original_filename"
        ).fetchall()

    assert records == [
        (first_response.json()["id"], "first.jpg"),
        (second_response.json()["id"], "second.png"),
    ]
