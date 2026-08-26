# Memora

Memora is a privacy-first personal photo intelligence platform for storing, viewing, and eventually searching personal photo collections using local AI.

The project is being built incrementally with an emphasis on clear architecture, local-first data ownership, testability, and backward-compatible evolution.

Memora currently supports end-to-end photo ingestion and browsing through a React frontend backed by FastAPI, SQLite, Pillow, and local filesystem storage.

> AI-powered semantic search is part of the roadmap and is not implemented yet.

---

## Current Status

Memora currently supports:

- React + TypeScript browser interface
- Single-photo JPEG/JPG/PNG upload from the browser
- FastAPI backend
- Pillow-based image validation
- Rejection of corrupt, fake, unsupported, and format-mismatched images
- UUID-based internal filenames
- Local original-photo storage
- Automatic local thumbnail generation
- Aspect-ratio-preserving thumbnails up to 400×400
- No thumbnail upscaling for small images
- SQLite metadata persistence
- Backward-compatible SQLite schema migrations
- Image dimensions for new uploads
- Typed Pydantic API response contracts
- Original image retrieval
- Thumbnail retrieval
- Responsive photo gallery
- Automatic fallback to original images for legacy photos without thumbnails
- Newest-first photo listing
- Configurable database, original-photo, and thumbnail locations
- Cleanup of partially created files when persistence fails
- Private filesystem paths that are never exposed through public JSON APIs
- 23 backend tests
- Frontend TypeScript validation and production builds

The current application can be used entirely through the browser:

```text
Select Photo
     |
     v
React + TypeScript
     |
     | POST /photos
     v
FastAPI
     |
     +-----------------------------+
     |                             |
     v                             v
Pillow Validation            UUID Generation
     |                             |
     +-------------+---------------+
                   |
                   v
          Original Photo Storage
                   |
                   v
           Thumbnail Generation
                   |
                   v
             SQLite Metadata
                   |
                   v
             GET /photos
                   |
                   v
            React Photo Gallery
```

---

## Architecture

```text
                        Memora

                  React + TypeScript
                         |
                         |
                 Vite development proxy
                         |
                         v
                      FastAPI
                  /       |       \
                 /        |        \
                v         v         v
            SQLite     Originals   Thumbnails
            Metadata      |            |
                          |            |
                          +------------+
                               |
                               v
                         Local Filesystem
```

SQLite acts as the metadata source of truth.

The filesystem stores original image binaries and generated thumbnails separately.

The frontend never receives internal filesystem paths. Image retrieval is performed using photo IDs that are resolved through persisted database metadata.

---

## Tech Stack

### Frontend

- React
- TypeScript
- Vite
- Plain CSS

### Backend

- Python
- FastAPI
- Pydantic
- Pillow
- SQLite
- Uvicorn

### Testing

- Pytest
- FastAPI TestClient

---

## Project Structure

```text
memora/
├── backend/
│   ├── app/
│   │   ├── database.py
│   │   ├── main.py
│   │   └── schemas.py
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── styles.css
│   ├── package.json
│   ├── pnpm-lock.yaml
│   └── vite.config.js
│
├── AGENTS.md
├── ARCHITECTURE.md
└── README.md
```

Generated user data is stored under `backend/data/` by default and is excluded from Git.

---

## Running Locally

### 1. Backend

From the repository root in Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt

uvicorn app.main:app --app-dir backend --reload
```

FastAPI runs at:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

---

### 2. Frontend

Open a second PowerShell terminal:

```powershell
cd frontend
corepack pnpm install
corepack pnpm dev
```

Open:

```text
http://localhost:5173
```

During local development, Vite proxies `/photos` requests to the FastAPI backend.

This avoids requiring broad CORS configuration solely for local development.

---

## Configuration

Memora supports environment-based local storage configuration.

### Original photos

```text
MEMORA_PHOTO_STORAGE_DIR
```

Default:

```text
backend/data/photos
```

### Thumbnails

```text
MEMORA_THUMBNAIL_STORAGE_DIR
```

Default:

```text
backend/data/thumbnails
```

### SQLite database

```text
MEMORA_DATABASE_PATH
```

Default:

```text
backend/data/memora.db
```

No machine-specific filesystem paths are hardcoded into the application.

---

## API

### `GET /health`

Returns backend health status.

```json
{
  "status": "ok"
}
```

---

### `POST /photos`

Uploads one JPEG, JPG, or PNG image using multipart form data.

Successful response:

```json
{
  "id": "<generated-uuid>",
  "original_filename": "<uploaded-filename>",
  "stored_filename": "<generated-uuid>.<extension>"
}
```

Before persistence, Memora validates the image contents using Pillow.

Invalid, corrupt, unsupported, or extension/format-mismatched files return HTTP 400.

A successful upload:

```text
validates image
→ extracts dimensions
→ generates UUID
→ stores original
→ generates thumbnail
→ persists metadata
```

If persistence fails, newly created original and thumbnail files are removed.

---

### `GET /photos`

Returns public photo metadata ordered newest-first.

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

Private values such as original filesystem paths and thumbnail filesystem paths are never returned.

Legacy records created before dimension support may contain:

```json
{
  "width": null,
  "height": null
}
```

---

### `GET /photos/{photo_id}/file`

Returns the original uploaded image.

The requested photo ID is first resolved through SQLite. The API does not construct filesystem paths directly from user-controlled URL values.

Possible results:

```text
200 → original image
404 → unknown photo or missing original file
```

---

### `GET /photos/{photo_id}/thumbnail`

Returns the locally generated thumbnail for a photo.

Possible results:

```text
200 → thumbnail image
404 → unknown photo, legacy photo without thumbnail, or missing thumbnail file
```

The React gallery requests thumbnails first.

For photos created before thumbnail support, the frontend automatically falls back to the original `/file` endpoint.

---

## Thumbnail Pipeline

New uploads generate a local thumbnail using Pillow.

```text
Original Image
      |
      v
Pillow
      |
      | max bounding box: 400×400
      | preserve aspect ratio
      | do not upscale
      v
Local Thumbnail
```

Original files remain byte-for-byte unchanged.

Originals and thumbnails are stored separately.

---

## Testing

Activate the Python environment and run:

```powershell
pytest backend\tests -v
```

Current backend suite:

```text
23 tests passing
```

Coverage includes:

- health endpoint
- valid JPEG and PNG uploads
- corrupt and fake-image rejection
- unsupported extensions
- UUID storage
- SQLite persistence
- deterministic photo ordering
- backward-compatible schema migration
- public-path privacy
- original image retrieval
- thumbnail generation
- aspect-ratio preservation
- thumbnail size limits
- prevention of thumbnail upscaling
- missing-file behavior
- missing-thumbnail behavior
- persistence-failure cleanup
- explicit OpenAPI response contracts

Frontend validation:

```powershell
cd frontend
corepack pnpm build
```

The build performs TypeScript validation before creating the production Vite bundle.

---

## Privacy Model

Privacy is a core architectural requirement of Memora.

Current design principles:

- Personal images remain on the user's machine.
- SQLite metadata remains local.
- AI models planned for future milestones are intended to operate locally where practical.
- Original filesystem paths are never exposed through public API responses.
- Photo IDs are resolved through persisted metadata instead of being treated as filesystem paths.
- Personal photos, databases, thumbnails, model weights, secrets, and generated user data must never be committed to Git.

The following directory is ignored by Git:

```text
backend/data/
```

---

## Current Project Scope

Memora's current milestone establishes the storage and presentation foundation required for future photo intelligence.

Implemented:

```text
Photo ingestion
→ validation
→ local persistence
→ metadata
→ thumbnails
→ retrieval
→ browser gallery
```

The next phase introduces metadata enrichment and machine-learning-based understanding without replacing the stable ingestion/storage foundation.

---

## Roadmap

### Photo Foundation

- [x] FastAPI backend
- [x] SQLite metadata persistence
- [x] Local original-photo storage
- [x] JPEG/JPG/PNG validation
- [x] Width and height extraction
- [x] Backward-compatible schema migrations
- [x] Typed API response models
- [x] Original image retrieval
- [x] React + TypeScript gallery
- [x] Browser photo upload
- [x] Local thumbnail generation
- [x] Thumbnail retrieval
- [x] Legacy-photo fallback

### Metadata Intelligence

- [ ] EXIF extraction
- [ ] Capture timestamps
- [ ] Camera/device metadata
- [ ] Location metadata where available
- [ ] Richer photo organization

### Semantic Intelligence

- [ ] OpenCLIP image embeddings
- [ ] Local vector index
- [ ] FAISS similarity search
- [ ] Natural-language photo search
- [ ] Hybrid semantic + metadata retrieval

### Visual Understanding

- [ ] YOLO object detection
- [ ] OCR
- [ ] Face detection
- [ ] Face clustering
- [ ] User-defined people names

### Product Evolution

- [ ] Full-photo viewer
- [ ] Search interface
- [ ] Large-library performance testing
- [ ] Background indexing
- [ ] Deployment architecture
- [ ] Production observability
- [ ] Storage and retrieval benchmarking

---

## Long-Term Vision

The long-term goal is to support queries such as:

```text
"photos of Dad at the beach"

"graduation pictures with my friends"

"screenshots containing a flight number"

"photos of dogs outdoors"

"pictures of me standing next to a car"
```

These queries will eventually combine multiple sources of information:

```text
Semantic embeddings
+ object detection
+ OCR
+ people
+ timestamps
+ metadata
```

while maintaining Memora's privacy-first design.

---

## Research Direction

Memora may also serve as an experimental platform for studying privacy-preserving multimodal retrieval over personal photo collections.

Potential future evaluation areas include:

```text
semantic retrieval quality
multimodal ranking
Recall@K
Precision@K
MRR / nDCG
indexing throughput
query latency
memory usage
storage overhead
local inference performance
```

Any research results will be based on measured experiments rather than assumed performance.

---

## Development Philosophy

Memora is intentionally being developed through small, testable milestones.

Each milestone follows the same process:

```text
define contract
→ implement
→ inspect
→ test
→ verify against real data
→ commit
→ push
```

The project avoids premature infrastructure complexity and introduces new components only when the workload or product requirements justify them.
