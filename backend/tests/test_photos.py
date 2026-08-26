import sqlite3
import shutil
from io import BytesIO
from collections.abc import Iterator
from contextlib import closing
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app


client = TestClient(app)


def create_image_bytes(
    image_format: str,
    width: int = 4,
    height: int = 3,
) -> bytes:
    output = BytesIO()
    Image.new("RGB", (width, height), color="red").save(output, format=image_format)
    return output.getvalue()


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
    ("original_filename", "content_type", "image_format"),
    [
        ("vacation.jpg", "image/jpeg", "JPEG"),
        ("vacation.png", "image/png", "PNG"),
    ],
)
def test_upload_supported_photo(
    temporary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
    original_filename: str,
    content_type: str,
    image_format: str,
) -> None:
    photo_directory, database_path = configure_test_paths(
        temporary_directory, monkeypatch
    )
    width, height = 7, 5
    content = create_image_bytes(image_format, width, height)

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
                uploaded_at,
                width,
                height
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
    assert record[6:] == (width, height)


@pytest.mark.parametrize("original_filename", ["fake.jpg", "fake.png"])
def test_upload_rejects_fake_image_contents(
    temporary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
    original_filename: str,
) -> None:
    photo_directory, database_path = configure_test_paths(
        temporary_directory, monkeypatch
    )

    response = client.post(
        "/photos",
        files={"file": (original_filename, b"not-a-real-image", "image/jpeg")},
    )

    assert response.status_code == 400
    assert not photo_directory.exists()
    assert not database_path.exists()


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
        files={"file": ("first.jpg", create_image_bytes("JPEG"), "image/jpeg")},
    )
    second_response = client.post(
        "/photos",
        files={"file": ("second.png", create_image_bytes("PNG"), "image/png")},
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


def test_list_photos_returns_empty_array(
    temporary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_test_paths(temporary_directory, monkeypatch)

    response = client.get("/photos")

    assert response.status_code == 200
    assert response.json() == []


def test_list_photos_returns_uploaded_photo_without_stored_path(
    temporary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_test_paths(temporary_directory, monkeypatch)
    width, height = 8, 6
    content = create_image_bytes("JPEG", width, height)

    upload_response = client.post(
        "/photos",
        files={"file": ("listed.jpg", content, "image/jpeg")},
    )
    response = client.get("/photos")

    assert upload_response.status_code == 200
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": upload_response.json()["id"],
            "original_filename": "listed.jpg",
            "stored_filename": upload_response.json()["stored_filename"],
            "file_size": len(content),
            "uploaded_at": response.json()[0]["uploaded_at"],
            "width": width,
            "height": height,
        }
    ]
    assert "stored_path" not in response.json()[0]


def test_list_photos_returns_newest_upload_first(
    temporary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, database_path = configure_test_paths(temporary_directory, monkeypatch)

    first_response = client.post(
        "/photos",
        files={"file": ("first.jpg", create_image_bytes("JPEG"), "image/jpeg")},
    )
    second_response = client.post(
        "/photos",
        files={"file": ("second.png", create_image_bytes("PNG"), "image/png")},
    )

    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute(
            "UPDATE photos SET uploaded_at = ? WHERE id = ?",
            ("2026-01-01T00:00:00+00:00", first_response.json()["id"]),
        )
        connection.execute(
            "UPDATE photos SET uploaded_at = ? WHERE id = ?",
            ("2026-01-02T00:00:00+00:00", second_response.json()["id"]),
        )
        connection.commit()

    response = client.get("/photos")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert response.status_code == 200
    assert [photo["id"] for photo in response.json()] == [
        second_response.json()["id"],
        first_response.json()["id"],
    ]


def test_existing_photos_table_is_migrated_without_losing_records(
    temporary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, database_path = configure_test_paths(temporary_directory, monkeypatch)
    existing_id = "existing-photo"

    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute(
            """
            CREATE TABLE photos (
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
            INSERT INTO photos VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                existing_id,
                "existing.jpg",
                "existing.jpg",
                "private/existing.jpg",
                123,
                "2026-01-01T00:00:00+00:00",
            ),
        )
        connection.commit()

    response = client.get("/photos")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": existing_id,
            "original_filename": "existing.jpg",
            "stored_filename": "existing.jpg",
            "file_size": 123,
            "uploaded_at": "2026-01-01T00:00:00+00:00",
            "width": None,
            "height": None,
        }
    ]
    assert "stored_path" not in response.json()[0]

    with closing(sqlite3.connect(database_path)) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(photos)").fetchall()
        }
        record_count = connection.execute("SELECT COUNT(*) FROM photos").fetchone()[0]

    assert {"width", "height"}.issubset(columns)
    assert record_count == 1
