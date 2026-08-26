import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.database import list_photo_metadata, save_photo_metadata


app = FastAPI(title="Memora")

SUPPORTED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png"}
EXPECTED_IMAGE_FORMATS = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG"}


def get_photo_storage_directory() -> Path:
    configured_directory = os.getenv("MEMORA_PHOTO_STORAGE_DIR")
    if configured_directory:
        return Path(configured_directory)

    return Path(__file__).resolve().parents[1] / "data" / "photos"


def validate_image(file: UploadFile, extension: str) -> tuple[int, int]:
    try:
        file.file.seek(0)
        with Image.open(file.file) as image:
            image.verify()

        file.file.seek(0)
        with Image.open(file.file) as image:
            image.load()
            image_format = image.format
            width, height = image.size
    except (
        Image.DecompressionBombError,
        OSError,
        SyntaxError,
        UnidentifiedImageError,
        ValueError,
    ) as error:
        raise HTTPException(status_code=400, detail="Invalid image file") from error
    finally:
        file.file.seek(0)

    if image_format != EXPECTED_IMAGE_FORMATS[extension]:
        raise HTTPException(status_code=400, detail="Invalid image file")

    return width, height


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/photos")
def list_photos() -> list[dict[str, str | int | None]]:
    return list_photo_metadata()


@app.post("/photos")
def upload_photo(file: UploadFile = File(...)) -> dict[str, str]:
    original_filename = file.filename or ""
    extension = Path(original_filename).suffix.lower()

    if extension not in SUPPORTED_PHOTO_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    width, height = validate_image(file, extension)
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
            width=width,
            height=height,
        )
    except Exception:
        stored_path.unlink(missing_ok=True)
        raise

    return {
        "id": photo_id,
        "original_filename": original_filename,
        "stored_filename": stored_filename,
    }
