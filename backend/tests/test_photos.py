from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


@pytest.mark.parametrize(
    ("original_filename", "content_type", "content"),
    [
        ("vacation.jpg", "image/jpeg", b"jpg-photo"),
        ("vacation.png", "image/png", b"png-photo"),
    ],
)
def test_upload_supported_photo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    original_filename: str,
    content_type: str,
    content: bytes,
) -> None:
    monkeypatch.setenv("MEMORA_PHOTO_STORAGE_DIR", str(tmp_path))

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
    assert (tmp_path / response_body["stored_filename"]).read_bytes() == content


def test_upload_rejects_unsupported_file_type(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MEMORA_PHOTO_STORAGE_DIR", str(tmp_path))

    response = client.post(
        "/photos",
        files={"file": ("notes.txt", b"not-a-photo", "text/plain")},
    )

    assert response.status_code == 400
    assert list(tmp_path.iterdir()) == []
