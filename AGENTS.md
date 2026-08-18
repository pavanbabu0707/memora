# Memora

## Goal

Build a privacy first personal AI photo intelligence platform.

The application should eventually allow users to import personal photos, understand their contents, recognize user approved people, detect objects, extract text, and search photos using natural language.

## Initial Stack

Frontend: React with TypeScript

Backend: Python with FastAPI

Database: SQLite for the first version

Image Storage: Local filesystem

AI Search: OpenCLIP image and text embeddings

Vector Search: FAISS

Object Detection: YOLO in a later milestone

## Engineering Rules

1. Keep frontend, backend, machine learning, and storage concerns separated.
2. Use Python type hints.
3. Write tests for backend functionality.
4. Do not hardcode filesystem paths.
5. Use environment based configuration when configuration is needed.
6. Do not introduce Redis, Kafka, Kubernetes, cloud infrastructure, microservices, or other infrastructure unless the project actually needs them.
7. Work in small milestones.
8. Do not implement future milestones unless explicitly requested.
9. Prefer clear and understandable code over clever abstractions.
10. Before making a major architectural change, explain why it is needed.
11. Run relevant tests after implementing changes.
12. Fix test failures before considering a task complete.
