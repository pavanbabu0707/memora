# Memora

Memora is a privacy-first personal photo intelligence platform being built incrementally.

## Current Status

Memora is in early development. The current implementation includes:

- FastAPI backend
- `GET /health` endpoint
- `POST /photos` endpoint
- Single JPG, JPEG, or PNG upload
- UUID-based stored filenames
- Configurable local photo storage
- Unsupported file type validation
- Pytest tests
- Uvicorn local development server

## Current Architecture

```text
Client
  |
  v
Uvicorn
  |
  v
FastAPI
  |
  v
Local Photo Storage
```

## Running Locally

From the repository root in Windows PowerShell:

1. Create a virtual environment:

   ```powershell
   python -m venv .venv
   ```

2. Activate the virtual environment:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

3. Install the backend requirements:

   ```powershell
   python -m pip install -r backend\requirements.txt
   ```

4. Start the Uvicorn development server:

   ```powershell
   uvicorn app.main:app --app-dir backend --reload
   ```

5. Open the interactive API documentation at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

6. Open the health endpoint at [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health).

The photo storage location can be configured by setting the `MEMORA_PHOTO_STORAGE_DIR` environment variable before starting the server. Without this setting, photos are stored under `backend/data/photos`.

## Testing

With the virtual environment activated, run:

```powershell
pytest backend\tests -v
```

The current test suite covers the health check, supported JPG and PNG uploads, and unsupported file type rejection.

## API

### `GET /health`

Returns the backend health status:

```json
{
  "status": "ok"
}
```

### `POST /photos`

Accepts one JPG, JPEG, or PNG file as multipart form data. A successful upload returns:

```json
{
  "id": "<generated-uuid>",
  "original_filename": "<uploaded-filename>",
  "stored_filename": "<generated-uuid>.<extension>"
}
```

Unsupported file types return HTTP 400.

## Privacy

- Uploaded photos are stored locally.
- `backend/data` is ignored by Git.
- Personal photos should never be committed to the repository.

## Roadmap

The following features are planned and are not yet implemented:

- SQLite photo metadata
- Photo listing
- Image metadata extraction
- Semantic image embeddings
- Natural-language search
- Object detection
- Face clustering
- OCR
