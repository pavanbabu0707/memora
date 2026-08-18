# Memora

## Goal

Build a privacy-first personal AI photo intelligence platform.

The application will eventually allow users to import personal photos, understand their contents, recognize user-approved people, detect objects, extract text, and search photos using natural language.

## Initial Stack

Frontend: React with TypeScript
Backend: Python with FastAPI
Database: SQLite initially
Image Storage: Local filesystem
Semantic AI: OpenCLIP
Vector Search: FAISS
Object Detection: YOLO in a later milestone

## Engineering Rules

1. Keep frontend, backend, machine learning, and storage concerns separated.
2. Use Python type hints.
3. Write tests for backend functionality.
4. Never hardcode filesystem paths.
5. Use environment-based configuration where appropriate.
6. Do not introduce Redis, Kafka, Kubernetes, cloud infrastructure, or microservices unless explicitly requested.
7. Work in small milestones.
8. Never implement future milestones unless explicitly requested.
9. Prefer simple, readable code over unnecessary abstractions.
10. Explain major architectural changes before implementing them.
11. Run relevant tests after changes.
12. Fix test failures before considering a task complete.
13. Never commit personal photos, model weights, secrets, API keys, databases, or generated user data to Git.
14. Respect user privacy as a core architectural requirement.
