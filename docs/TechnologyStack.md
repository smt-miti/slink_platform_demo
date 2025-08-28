## MVP Technology Stack

| Area           | Choice (MVP) | Why this for MVP |
|----------------|--------------|------------------|
| **API**        | Python + FastAPI | Fast to build/iterate; type-validated models; clear auto-generated docs. |
| **App Server** | Uvicorn (ASGI)   | Lightweight, async, great for I/O-bound redirects and high concurrency. |
| **Containerization** | Docker | One-command run, reproducible, isolates dependencies. |
| **Storage**    | In-memory store (default); config-swappable to Postgres (Docker) | Zero setup for quick runs; flip config to test with real DB. |
| **Docs**       | OpenAPI/Swagger UI (FastAPI docs) | Self-documenting endpoints for reviewers. |
| **Logging**    | Uvicorn access logs + JSON logs to stdout | Simple and effective for demos/containers. |
| **Configuration** | Config variables  | Clean separation; enables storage backend swapping easily. |
