import os
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile


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

    with (storage_directory / stored_filename).open("wb") as stored_photo:
        shutil.copyfileobj(file.file, stored_photo)

    return {
        "id": photo_id,
        "original_filename": original_filename,
        "stored_filename": stored_filename,
    }
