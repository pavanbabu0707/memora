import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.database import save_photo_metadata


app = FastAPI(title="Memora")

SUPPORTED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def get_photo_storage_directory() -> Path:
    configured_directory = os.getenv("MEMORA_PHOTO_STORAGE_DIR")
    if configured_directory:
        return Path(configured_directory)

    return Path(__file__).resolve().parents[1] / "data" / "photos"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/photos")
def upload_photo(file: UploadFile = File(...)) -> dict[str, str]:
    original_filename = file.filename or ""
    extension = Path(original_filename).suffix.lower()

    if extension not in SUPPORTED_PHOTO_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    photo_id = str(uuid4())
    stored_filename = f"{photo_id}{extension}"
    storage_directory = get_photo_storage_directory()
    storage_directory.mkdir(parents=True, exist_ok=True)
    stored_path = storage_directory / stored_filename

    with stored_path.open("wb") as stored_photo:
        shutil.copyfileobj(file.file, stored_photo)

    try:
        save_photo_metadata(
            photo_id=photo_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            stored_path=stored_path,
            file_size=stored_path.stat().st_size,
            uploaded_at=datetime.now(UTC).isoformat(),
        )
    except Exception:
        stored_path.unlink(missing_ok=True)
        raise

    return {
        "id": photo_id,
        "original_filename": original_filename,
        "stored_filename": stored_filename,
    }
