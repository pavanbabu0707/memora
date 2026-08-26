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

from app import main as main_module
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
    thumbnail_directory = temporary_directory / "thumbnails"
    database_path = temporary_directory / "memora.db"
    monkeypatch.setenv("MEMORA_PHOTO_STORAGE_DIR", str(photo_directory))
    monkeypatch.setenv("MEMORA_THUMBNAIL_STORAGE_DIR", str(thumbnail_directory))
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


@pytest.mark.parametrize(
    ("original_filename", "image_format", "content_type"),
    [
        ("wide.jpg", "JPEG", "image/jpeg"),
        ("wide.png", "PNG", "image/png"),
    ],
)
def test_upload_creates_aspect_preserving_thumbnail(
    temporary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
    original_filename: str,
    image_format: str,
    content_type: str,
) -> None:
    photo_directory, database_path = configure_test_paths(
        temporary_directory, monkeypatch
    )
    thumbnail_directory = temporary_directory / "thumbnails"
    content = create_image_bytes(image_format, width=800, height=200)

    upload_response = client.post(
        "/photos",
        files={"file": (original_filename, content, content_type)},
    )

    assert upload_response.status_code == 200
    photo_id = upload_response.json()["id"]
    thumbnail_path = thumbnail_directory / f"{photo_id}{Path(original_filename).suffix}"
    assert thumbnail_path.is_file()
    with Image.open(thumbnail_path) as thumbnail:
        assert thumbnail.size == (400, 100)

    assert (photo_directory / upload_response.json()["stored_filename"]).read_bytes() == content

    thumbnail_response = client.get(f"/photos/{photo_id}/thumbnail")
    assert thumbnail_response.status_code == 200
    assert thumbnail_response.headers["content-type"] == content_type
    assert thumbnail_response.content == thumbnail_path.read_bytes()

    with closing(sqlite3.connect(database_path)) as connection:
        stored_thumbnail = connection.execute(
            "SELECT thumbnail_filename, thumbnail_path FROM photos WHERE id = ?",
            (photo_id,),
        ).fetchone()

    assert stored_thumbnail == (thumbnail_path.name, str(thumbnail_path))
    public_responses = [upload_response.json(), client.get("/photos").json()[0]]
    assert all("thumbnail_path" not in response for response in public_responses)
    assert all(str(thumbnail_directory) not in str(response) for response in public_responses)


def test_thumbnail_does_not_upscale_small_photo(
    temporary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_test_paths(temporary_directory, monkeypatch)
    upload_response = client.post(
        "/photos",
        files={"file": ("small.png", create_image_bytes("PNG", 40, 30), "image/png")},
    )
    thumbnail_path = (
        temporary_directory
        / "thumbnails"
        / f"{upload_response.json()['id']}.png"
    )

    assert upload_response.status_code == 200
    with Image.open(thumbnail_path) as thumbnail:
        assert thumbnail.size == (40, 30)


def test_upload_cleans_up_original_and_thumbnail_when_persistence_fails(
    temporary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    photo_directory, _ = configure_test_paths(temporary_directory, monkeypatch)
    thumbnail_directory = temporary_directory / "thumbnails"

    def fail_to_save(**_kwargs: object) -> None:
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(main_module, "save_photo_metadata", fail_to_save)

    with pytest.raises(RuntimeError, match="database unavailable"):
        client.post(
            "/photos",
            files={"file": ("cleanup.jpg", create_image_bytes("JPEG"), "image/jpeg")},
        )

    assert list(photo_directory.iterdir()) == []
    assert list(thumbnail_directory.iterdir()) == []


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

    assert {"width", "height", "thumbnail_filename", "thumbnail_path"}.issubset(
        columns
    )
    assert record_count == 1
    assert client.get(f"/photos/{existing_id}/thumbnail").status_code == 404


@pytest.mark.parametrize(
    ("original_filename", "image_format", "content_type"),
    [
        ("retrieved.jpg", "JPEG", "image/jpeg"),
        ("retrieved.png", "PNG", "image/png"),
    ],
)
def test_retrieve_uploaded_photo_file(
    temporary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
    original_filename: str,
    image_format: str,
    content_type: str,
) -> None:
    photo_directory, _ = configure_test_paths(temporary_directory, monkeypatch)
    content = create_image_bytes(image_format)
    upload_response = client.post(
        "/photos",
        files={"file": (original_filename, content, content_type)},
    )

    response = client.get(f"/photos/{upload_response.json()['id']}/file")

    assert upload_response.status_code == 200
    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-type"] == content_type
    assert b"stored_path" not in response.content
    assert str(photo_directory).encode() not in response.content
    assert all(str(photo_directory) not in value for value in response.headers.values())


def test_retrieve_unknown_photo_returns_not_found(
    temporary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_test_paths(temporary_directory, monkeypatch)

    response = client.get("/photos/unknown-photo/file")

    assert response.status_code == 404


def test_retrieve_unknown_photo_thumbnail_returns_not_found(
    temporary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_test_paths(temporary_directory, monkeypatch)

    response = client.get("/photos/unknown-photo/thumbnail")

    assert response.status_code == 404


def test_retrieve_photo_with_missing_file_returns_not_found(
    temporary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    photo_directory, _ = configure_test_paths(temporary_directory, monkeypatch)
    upload_response = client.post(
        "/photos",
        files={"file": ("missing.jpg", create_image_bytes("JPEG"), "image/jpeg")},
    )
    stored_path = photo_directory / upload_response.json()["stored_filename"]
    stored_path.unlink()

    response = client.get(f"/photos/{upload_response.json()['id']}/file")

    assert upload_response.status_code == 200
    assert response.status_code == 404


def test_retrieve_photo_with_missing_thumbnail_returns_not_found(
    temporary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_test_paths(temporary_directory, monkeypatch)
    upload_response = client.post(
        "/photos",
        files={"file": ("missing.jpg", create_image_bytes("JPEG"), "image/jpeg")},
    )
    thumbnail_path = (
        temporary_directory
        / "thumbnails"
        / f"{upload_response.json()['id']}.jpg"
    )
    thumbnail_path.unlink()

    response = client.get(f"/photos/{upload_response.json()['id']}/thumbnail")

    assert upload_response.status_code == 200
    assert response.status_code == 404
