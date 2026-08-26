import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError

from app.database import (
    get_photo_file_metadata,
    get_photo_thumbnail_metadata,
    list_photo_metadata,
    save_photo_metadata,
)
from app.schemas import PhotoMetadataResponse, PhotoUploadResponse


app = FastAPI(title="Memora")

SUPPORTED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png"}
EXPECTED_IMAGE_FORMATS = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG"}
IMAGE_MEDIA_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
THUMBNAIL_MAX_SIZE = (400, 400)


def get_photo_storage_directory() -> Path:
    configured_directory = os.getenv("MEMORA_PHOTO_STORAGE_DIR")
    if configured_directory:
        return Path(configured_directory)

    return Path(__file__).resolve().parents[1] / "data" / "photos"


def get_thumbnail_storage_directory() -> Path:
    configured_directory = os.getenv("MEMORA_THUMBNAIL_STORAGE_DIR")
    if configured_directory:
        return Path(configured_directory)

    return Path(__file__).resolve().parents[1] / "data" / "thumbnails"


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


def create_thumbnail(source_path: Path, thumbnail_path: Path, image_format: str) -> None:
    with Image.open(source_path) as image:
        image.thumbnail(THUMBNAIL_MAX_SIZE, Image.Resampling.LANCZOS)
        image.save(thumbnail_path, format=image_format)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/photos", response_model=list[PhotoMetadataResponse])
def list_photos() -> list[dict[str, str | int | None]]:
    return list_photo_metadata()


@app.post("/photos", response_model=PhotoUploadResponse)
def upload_photo(file: UploadFile = File(...)) -> dict[str, str]:
    original_filename = file.filename or ""
    extension = Path(original_filename).suffix.lower()

    if extension not in SUPPORTED_PHOTO_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    width, height = validate_image(file, extension)
    photo_id = str(uuid4())
    stored_filename = f"{photo_id}{extension}"
    thumbnail_filename = f"{photo_id}{extension}"
    storage_directory = get_photo_storage_directory()
    thumbnail_directory = get_thumbnail_storage_directory()
    storage_directory.mkdir(parents=True, exist_ok=True)
    thumbnail_directory.mkdir(parents=True, exist_ok=True)
    stored_path = storage_directory / stored_filename
    thumbnail_path = thumbnail_directory / thumbnail_filename

    try:
        with stored_path.open("wb") as stored_photo:
            shutil.copyfileobj(file.file, stored_photo)

        create_thumbnail(stored_path, thumbnail_path, EXPECTED_IMAGE_FORMATS[extension])
        save_photo_metadata(
            photo_id=photo_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            stored_path=stored_path,
            file_size=stored_path.stat().st_size,
            uploaded_at=datetime.now(UTC).isoformat(),
            width=width,
            height=height,
            thumbnail_filename=thumbnail_filename,
            thumbnail_path=thumbnail_path,
        )
    except Exception:
        stored_path.unlink(missing_ok=True)
        thumbnail_path.unlink(missing_ok=True)
        raise

    return {
        "id": photo_id,
        "original_filename": original_filename,
        "stored_filename": stored_filename,
    }


@app.get("/photos/{photo_id}/file", response_class=FileResponse)
def get_photo_file(photo_id: str) -> FileResponse:
    metadata = get_photo_file_metadata(photo_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail="Photo not found")

    stored_path = Path(metadata["stored_path"])
    media_type = IMAGE_MEDIA_TYPES.get(Path(metadata["stored_filename"]).suffix.lower())
    if not stored_path.is_file() or media_type is None:
        raise HTTPException(status_code=404, detail="Photo file not found")

    return FileResponse(path=stored_path, media_type=media_type)


@app.get("/photos/{photo_id}/thumbnail", response_class=FileResponse)
def get_photo_thumbnail(photo_id: str) -> FileResponse:
    metadata = get_photo_thumbnail_metadata(photo_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail="Photo not found")

    thumbnail_filename = metadata["thumbnail_filename"]
    thumbnail_path_value = metadata["thumbnail_path"]
    if thumbnail_filename is None or thumbnail_path_value is None:
        raise HTTPException(status_code=404, detail="Photo thumbnail not found")

    thumbnail_path = Path(thumbnail_path_value)
    media_type = IMAGE_MEDIA_TYPES.get(Path(thumbnail_filename).suffix.lower())
    if not thumbnail_path.is_file() or media_type is None:
        raise HTTPException(status_code=404, detail="Photo thumbnail not found")

    return FileResponse(path=thumbnail_path, media_type=media_type)
