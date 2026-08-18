# Memora V1 Architecture

Memora V1 is the smallest working version of the project.

## V1 Goal

A user can upload personal photos to a local backend and retrieve a list of uploaded photos.

## Architecture

```text
+--------+
| Client |
+--------+
    |
    v
+-----------------+
| FastAPI backend |
+-----------------+
    |
    v
+-----------------------------------+
| Photo storage on local filesystem |
+-----------------------------------+
    |
    v
+--------------------------+
| SQLite metadata database |
+--------------------------+
```

The client sends photo uploads and list requests to the FastAPI backend. The backend stores photo files on the local filesystem and records their metadata in SQLite.

## V1 Responsibilities

1. Accept JPG, JPEG, and PNG uploads.
2. Generate a unique ID for each photo.
3. Save uploaded photos locally.
4. Store photo metadata in SQLite:
   - id
   - original filename
   - stored path
   - file size
   - width
   - height
   - uploaded timestamp
5. Provide an endpoint to list uploaded photos.
6. Include backend tests.

## Explicitly Out of Scope for V1

- React frontend
- OpenCLIP
- FAISS
- YOLO
- facial recognition
- OCR
- authentication
- Redis
- background workers
- Docker
- cloud deployment
