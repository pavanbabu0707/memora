# Memora

Memora is a privacy-first personal photo intelligence platform being built incrementally. The project is in early development and currently provides a local-first V1 backend for uploading and listing photos.

## Current Status

Implemented today:

- FastAPI backend with `GET /health`, `POST /photos`, and `GET /photos`
- Single JPEG, JPG, or PNG upload per request
- Real image validation and dimension extraction with Pillow
- Rejection of corrupt, fake, unsupported, or format-mismatched images
- UUID-based stored filenames
- Configurable local photo storage
- SQLite metadata persistence with a backward-compatible schema migration
- Width and height for new uploads; migrated older rows may contain `null`
- Newest-first photo metadata listing
- Private storage paths that are never exposed by the API
- Filesystem cleanup when database persistence fails
- Pytest coverage for health, uploads, validation, persistence, migration, and listing
- Uvicorn local development server

No AI, semantic search, or frontend functionality is implemented yet.

## Current Architecture

```text
Client
  |
  v
FastAPI
 | \
 |  \
 v   v
SQLite   Local Photo Storage
```

SQLite stores photo metadata. The local filesystem stores the image binaries.

## Running Locally

From the repository root in Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

Open the interactive API documentation at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) or the health endpoint at [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health).

Configuration:

- `MEMORA_PHOTO_STORAGE_DIR` sets the local image directory. The default is `backend/data/photos`.
- `MEMORA_DATABASE_PATH` sets the SQLite database path. The default is `backend/data/memora.db`.

## API

### `GET /health`

Returns the backend health status:

```json
{
  "status": "ok"
}
```

### `POST /photos`

Accepts one valid JPEG, JPG, or PNG image as multipart form data. A successful upload returns:

```json
{
  "id": "<generated-uuid>",
  "original_filename": "<uploaded-filename>",
  "stored_filename": "<generated-uuid>.<extension>"
}
```

Invalid, corrupt, unsupported, or extension/format-mismatched images return HTTP 400 without leaving a photo file or metadata record.

### `GET /photos`

Returns photo metadata ordered by `uploaded_at` from newest to oldest:

```json
[
  {
    "id": "<generated-uuid>",
    "original_filename": "<uploaded-filename>",
    "stored_filename": "<generated-uuid>.<extension>",
    "file_size": 12345,
    "uploaded_at": "<UTC-timestamp>",
    "width": 1920,
    "height": 1080
  }
]
```

Rows created before dimension support may return `null` for `width` and `height`. The private `stored_path` value is never returned.

## Testing

With the virtual environment activated, run:

```powershell
pytest backend\tests -v
```

## Privacy

- Images and metadata remain on the local machine.
- `backend/data` is ignored by Git.
- Personal photos, databases, and generated user data should never be committed.

## Roadmap

The following features are planned and not implemented:

- Serving and retrieving image files
- Explicit API response models
- Thumbnails
- Richer metadata and EXIF extraction
- OpenCLIP embeddings
- FAISS semantic search
- Natural-language photo search
- YOLO object detection
- OCR
- Face clustering and naming
- Frontend
