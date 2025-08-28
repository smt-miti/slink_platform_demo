# Slink Platform — URL Shortener 

A modular **FastAPI URL shortener** with strategy-driven code generation (Bitly-like sequential or SHA-256 deterministic) complete with analytics and modular storage (in-memory/ backend)

## Features
- **Short URL Creation**
  - Create short links with optional user-provided alias (vanity).
  - Deterministic or sequential Base62 codes (config-driven).
  - Duplicate prevention (long URL or alias)
  - Valid URL format enforcement
  - Allowed characters: `0-9`, `a-z`, `A-Z`

- **Client Redirection**
  - RESTful API + browser support
  - Redirection to original URL
  - Tracks click source (`api` vs `browser`)

- **Analytics**
  - Tracks **total clicks**
  - Records last click timestamp

- **Storage**
  - In-memory/ postgres storage 
  - Configurable storage selection

## 📂 Repository Structure
```
shortlink-platform/
│
├── slink_platform/                 # Core service package
│   ├── analytics/                  # Analytics engine
│   │   ├── __init__.py
│   │   ├── analytics.py            # Analytics implementation
│   │   └── base.py                 # Abstract analytics backend
│   │
│   ├── manager/                    # Business logic
│   │   ├── __init__.py
│   │   ├── slink_manager.py        # Core manager (validation, dedupe, aliasing)
│   │   └── strategies.py           # Encoding strategies
│   │
│   ├── storage/                    # Storage backends
│   │   ├── __init__.py
│   │   ├── base.py                 # Abstract storage interface
│   │   ├── storage.py              # Storage service
│   │   ├── db_storage.py           # Postgres DB impl
│   │   └── storage_factory.py      # Storage selection service
│   │
│   └── __init__.py
│
├── tests/                          # Pytest suite
│   ├── unit/                       # Unit tests
│   ├── integration/                # Integration tests
│   ├── nfr/                        # nfr test
|   ├── conftest.py                 # pytest fixtures for test suite
│   └── __init__.py
│
├── docs/                           # Documentation
│   ├── HLSD.md                     # High Level Design doc
|   ├── RELEASE_NOTES.md
|   ├── strategy_configuration.md   # short-code strategy configuration
|   ├── TechnologyStack.md          # Technology used in slink platform
|   └── URL_Encoding_Algorithms.md  # Strategy comparision
│
├── main.py                         # FastAPI entrypoint (with app factory)
├── requirements.txt                # Runtime deps
├── README.md                       # This file
├── docker-compose.yml              # Docker compose file
├── Dockerfile                      
└── Makefile                       
```
### 1. Install dependencies

```bash 
python -m venv .venv
source .venv/Scripts/activate 

pip install -r requirements.txt
```
#### ✅ Testing
```
pytest -v 
```

#### Code Coverage
```
pytest --cov=slink_platform --cov-report=term-missing --cov-report=html
```

#### Run NFR/Performance tests

```bash
RUN_NFR=1 NFR_CONCURRENCY=8 NFR_REQUESTS=4000   NFR_TARGET_REDIRECT_QPS=800 NFR_TARGET_REDIRECT_P95_MS=5   pytest tests/nfr -vv
```
Switch strategy from deterministic to sequential for slink creation and run NFR
```
export SLINK_CODE_STRATEGY=sequential
RUN_NFR=1 NFR_CONCURRENCY=8 NFR_REQUESTS=4000   NFR_TARGET_REDIRECT_QPS=800 NFR_TARGET_REDIRECT_P95_MS=5   pytest tests/nfr -vv
```

### 2. Run the FastAPI app

```bash
uvicorn main:app --reload
```
- API docs at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### API (Swagger UI)
- Go to http://127.0.0.1:8000/docs
- `POST /slink` body: `{ "url": "https://example.com", "alias": "mycode" }`
  - Query: `check_reachable=true|false` (defaults off; enforced for localhost in tests)
- `GET /{code}` -> 307 redirect to original URL

#### Testing from terminal
```
curl -X POST "http://localhost:8000/slink" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com"}'
```

```
curl -i "http://localhost:8000/slink/3NBE4XKN"
```

### Config (env vars)

- `SLINK_CODE_STRATEGY`: `sha256` (default) | `sequential` | `hmac-sha256` | `random`
- `SLINK_CODE_LENGTH`: default 8 for deterministic strategies
- `SLINK_CODE_MIN_LENGTH`: default 6 for sequential strategy
- `SLINK_SEQ_START`: starting counter for sequential
- `SLINK_SHARD_PREFIX`: optional prefix for sequential (e.g., region code)

### Docker

#### Prerequisites

- Docker Desktop (Windows/macOS) or Docker Engine (Linux)
- (Windows) Enable WSL2 backend in Docker Desktop

Powershell Commands (for sequential strategy)
```powershell 
cd C:\Users\Hp\Documents\Ruchi_Office_Important\DE_Project\slink_platform_demo

docker build -t slink_platform_demo .
docker run --rm -p 8000:8000 `
  -e SLINK_CODE_STRATEGY=sequential `
  slink-platform
```

Powershell Commands (for deterministic strategy)
```powershell 
cd C:\Users\Hp\Documents\Ruchi_Office_Important\DE_Project\slink_platform_demo

docker build -t slink_platform_demo .
docker run --rm -p 8000:8000 slink_platform_demo
```

#### Build
From the repo root:
```
docker build -t slink-platform .
```

#### Run
- Foreground (see logs in the terminal)
```
docker run --rm -p 8000:8000 \
  -e SLINK_CODE_STRATEGY=sequential \
  -e SLINK_SEQ_START=100000 \
  --name slink \
  slink-platform
```

#### Test the container
Git Bash 
```
# Health (if implemented)
curl http://localhost:8000/health

# Create a slink
curl -s -X POST "http://localhost:8000/slink" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com"}'

# Replace CODE below with the "slink" value from the previous response
curl -i "http://localhost:8000/slink/CODE"
```

#### API docs (browser)

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

#### Logs, shell, stop
#### Tail logs (detached container)
```docker logs -f slink```

#### Shell inside
```docker exec -it slink sh```

#### Stop & remove
```docker rm -f slink```

### Make
#### Local development
```
make install     # create .venv and install requirements
make run         # run FastAPI app locally (uvicorn)
make test        # run unit tests
make coverage    # run tests with coverage report (htmlcov/index.html)
```

#### NFR / Performance tests
```
make nfr             # run NFR tests (default settings)
make nfr-sequential  # run NFR tests with sequential code strategy
```

#### Docker
```
make docker-build    # build the Docker image (slink-platform)
make docker-run-seq  # run container with sequential strategy
make docker-run-det  # run container with deterministic strategy
make docker-logs     # follow container logs
make docker-shell    # open shell inside container
make docker-stop     # stop and remove running container
```
#### Cleanup
```
make clean
```
Removes .venv, caches, and stops/removes any running container named slink.


## 🧩 Extensibility

- **Storage**: Swap in DB (Postgres, Redis) by extending `BaseStorage`.
- **Analytics**: Extend `BaseAnalytics` for DB/stream-backed analytics.
- **Encoding**: Add new strategies in `strategies.py` (beyond deterministic base62).

## 🔮 Future Improvements

- Sharded DB backend with replication
- Async analytics pipeline (Kafka, ClickHouse)
- Expiry policies & cleanup
- Rate limiting & abuse protection
- Custom domains for shortened URLs
---

## Notes
- The default strategy in this build is `sha256` to keep unit/integration tests deterministic. Switch to Bitly-like sequential by setting `SLINK_CODE_STRATEGY=sequential`.
- Perf/NFR tests are illustrative; for real load use a proper tool (wrk/k6/Locust).
