# Memora Architecture

Memora is a privacy-first personal photo intelligence platform being developed incrementally.

This document describes the current system architecture at the photo-foundation checkpoint. AI-powered semantic search, object detection, OCR, and face understanding are future layers and are not implemented yet.

---

## Current System

```text
                         Browser
                            |
                            v
                  React + TypeScript
                            |
                    Vite dev proxy
                            |
                            v
                         FastAPI
                     /      |      \
                    /       |       \
                   v        v        v
               SQLite   Originals  Thumbnails
               Metadata      \       /
                              \     /
                               v   v
                         Local Filesystem
```

The application currently consists of four main areas:

1. React frontend
2. FastAPI backend
3. SQLite metadata database
4. Local filesystem storage

The backend is the boundary between the browser and local persisted data.

---

## Design Principles

Memora currently follows these architectural principles:

- Local-first storage
- Privacy by default
- Small incremental milestones
- SQLite as the metadata source of truth
- Filesystem paths remain backend-internal
- UUID-based internal image names
- Backward-compatible schema evolution
- Failure-safe filesystem/database behavior
- Explicit public API contracts
- No premature distributed infrastructure
- AI components added only after the storage foundation is stable

---

## Frontend

Technology:

```text
React
TypeScript
Vite
Plain CSS
```

The frontend currently provides:

- photo gallery
- single-photo browser upload
- loading state
- empty-library state
- API error state
- upload error handling
- responsive photo grid
- thumbnail rendering
- fallback to the original image for legacy photos without thumbnails

The frontend communicates with the backend using relative `/photos` requests.

During local development:

```text
Browser
   |
   v
localhost:5173
   |
   v
Vite proxy
   |
   v
127.0.0.1:8000
   |
   v
FastAPI
```

This avoids requiring permissive CORS settings only for local development.

---

## Backend

Technology:

```text
Python
FastAPI
Pydantic
Pillow
SQLite
```

The FastAPI backend currently owns:

- image ingestion
- file validation
- UUID generation
- image dimension extraction
- original-file persistence
- thumbnail generation
- metadata persistence
- schema migration
- metadata listing
- original image retrieval
- thumbnail retrieval
- public response validation
- cleanup after failed persistence

---

## Photo Upload Flow

```text
POST /photos
     |
     v
Validate extension
     |
     v
Validate real image contents with Pillow
     |
     v
Extract dimensions
     |
     v
Generate UUID
     |
     +----------------------+
     |                      |
     v                      v
Store original       Generate thumbnail
     |                      |
     +-----------+----------+
                 |
                 v
          Persist metadata
                 |
                 v
             SQLite
                 |
                 v
       Return public response
```

Supported formats:

- JPG
- JPEG
- PNG

Image validation happens before permanent persistence.

The filename extension must match the decoded image format.

---

## Original Image Storage

Original photos are stored under a configurable directory.

Environment variable:

```text
MEMORA_PHOTO_STORAGE_DIR
```

Default:

```text
backend/data/photos
```

Stored filenames are generated from the photo UUID:

```text
<photo-id>.<extension>
```

The original user filename is retained only as metadata and is never used to select an arbitrary filesystem location.

Original uploaded bytes remain unchanged after successful storage.

---

## Thumbnail Storage

New uploads generate a local thumbnail with Pillow.

Environment variable:

```text
MEMORA_THUMBNAIL_STORAGE_DIR
```

Default:

```text
backend/data/thumbnails
```

Current thumbnail policy:

```text
maximum bounding box: 400x400
preserve aspect ratio
do not upscale smaller images
LANCZOS resampling
```

Original and thumbnail files are stored independently.

Legacy photos created before thumbnail support may have no thumbnail.

The frontend handles this by:

```text
request thumbnail
      |
      | failure
      v
request original
```

---

## Metadata Storage

SQLite is currently the metadata source of truth.

Environment variable:

```text
MEMORA_DATABASE_PATH
```

Default:

```text
backend/data/memora.db
```

The current `photos` table contains:

```text
id
original_filename
stored_filename
stored_path
file_size
uploaded_at
width
height
thumbnail_filename
thumbnail_path
```

Internal path fields are persisted because the backend needs them to resolve files.

They are never included in public photo metadata responses.

---

## Schema Evolution

Memora uses small backward-compatible SQLite migrations.

The backend inspects the existing table using:

```sql
PRAGMA table_info(photos)
```

and conditionally adds newer columns using `ALTER TABLE`.

Examples added after the original schema:

```text
width
height
thumbnail_filename
thumbnail_path
```

Older records remain valid.

For example:

```text
legacy photo
width              = NULL
height             = NULL
thumbnail_filename = NULL
thumbnail_path     = NULL
```

No existing record should be deleted simply because a newer feature was introduced.

A dedicated migration system may replace this approach later if schema complexity grows enough to justify it.

---

## Public API

### Health

```text
GET /health
```

Returns application health status.

### Upload

```text
POST /photos
```

Accepts one JPEG/JPG/PNG image.

### Photo list

```text
GET /photos
```

Returns public metadata newest-first.

### Original image

```text
GET /photos/{photo_id}/file
```

Returns the original stored image.

### Thumbnail

```text
GET /photos/{photo_id}/thumbnail
```

Returns the generated thumbnail when available.

---

## File Resolution Security Boundary

A client is never allowed to provide a filesystem path directly.

For example, the backend does not do:

```text
/photos/../../private-file
        |
        v
filesystem
```

Instead:

```text
photo_id from request
        |
        v
parameterized SQLite lookup
        |
        v
trusted persisted metadata
        |
        v
stored filesystem path
```

The user-controlled ID therefore selects a database record rather than directly selecting a filesystem location.

---

## Public API Models

JSON responses are defined using explicit Pydantic models.

Current public models include:

```text
PhotoUploadResponse
PhotoMetadataResponse
```

Public metadata intentionally excludes:

```text
stored_path
thumbnail_path
```

Additional response fields are forbidden so accidental internal-field leakage causes validation failure rather than silently becoming part of the API contract.

Binary image endpoints remain `FileResponse` endpoints and are separate from the JSON model layer.

---

## Failure Consistency

Photo ingestion touches both the filesystem and SQLite.

Current upload behavior is designed to avoid leaving partial data.

```text
write original
      |
generate thumbnail
      |
persist SQLite row
```

If thumbnail creation or database persistence fails:

```text
delete newly created original
delete newly created thumbnail
propagate failure
```

This prevents orphan files from remaining after an unsuccessful upload operation.

---

## Photo Listing

SQLite is the source used for listing photos.

The backend does not scan the filesystem to reconstruct the gallery.

Current ordering:

```text
uploaded_at DESC
```

so newly uploaded photos appear first.

---

## Privacy Boundary

Current local-first data:

```text
backend/data/
├── memora.db
├── photos/
└── thumbnails/
```

`backend/data/` is ignored by Git.

The project must never commit:

- personal photos
- SQLite user databases
- generated thumbnails
- model weights
- credentials
- API keys
- secrets
- generated private user data

The browser receives photo IDs and public metadata, not machine-local filesystem paths.

---

## Testing Strategy

Backend behavior is covered by Pytest and FastAPI TestClient.

The current suite covers:

- health
- supported uploads
- corrupt image rejection
- extension/format validation
- UUID storage
- image dimensions
- SQLite persistence
- legacy schema migration
- public response contracts
- original file retrieval
- thumbnail generation
- aspect-ratio preservation
- no thumbnail upscaling
- unknown IDs
- missing physical files
- missing thumbnails
- persistence failure cleanup
- private path protection

Current checkpoint:

```text
23 backend tests passing
```

The frontend is validated with:

```text
TypeScript type-check
Vite production build
manual browser verification
```

---

## Current Scaling Model

The current design intentionally targets a local personal photo library.

SQLite and local filesystem storage remain appropriate at the present scale.

As the library grows, likely evidence-driven changes include:

```text
pagination / cursor-based listing
        |
        v
frontend virtualization
        |
        v
background AI indexing
        |
        v
vector retrieval
        |
        v
large-library benchmarking
```

Infrastructure such as PostgreSQL, object storage, task queues, Redis, or distributed services should only be introduced when measured requirements justify them.

---

## Planned Intelligence Layer

The next major architectural phase adds photo understanding.

Planned direction:

```text
Photo
  |
  +---- metadata / EXIF
  |
  +---- OpenCLIP embedding
  |
  +---- YOLO objects
  |
  +---- OCR text
  |
  +---- faces / people
  |
  v
Multimodal searchable representation
```

Semantic retrieval is expected to evolve toward:

```text
Natural-language query
        |
        v
OpenCLIP text embedding
        |
        v
FAISS vector search
        |
        v
candidate photo IDs
        |
        v
metadata / object / OCR / people signals
        |
        v
ranked photo results
```

None of this AI functionality is currently implemented.

---

## Explicitly Not Implemented Yet

- EXIF enrichment
- OpenCLIP embeddings
- FAISS search
- natural-language search
- YOLO detection
- OCR
- face detection
- face clustering
- people naming
- authentication
- background job processing
- Redis
- cloud object storage
- distributed services
- production deployment
- production observability

---

## Architectural Evolution

Memora is intentionally designed to evolve based on demonstrated requirements rather than speculative complexity.

Current progression:

```text
V1
local upload + SQLite metadata
        |
        v
V2 foundation
retrieval + typed API + React gallery + browser upload + thumbnails
        |
        v
next phase
metadata intelligence + ML embeddings + semantic retrieval
        |
        v
later
multimodal understanding + scale testing + deployment
```

Each architectural change should remain testable, explainable, and justified by an actual product or workload requirement.
