# Makefile for slink_platform_demo
# Use from Git Bash:  make <target>

.PHONY: install run test coverage nfr docker-build docker-run-seq docker-run-det docker-logs docker-shell docker-stop clean

# --- Local setup & run ---

install:
	python -m venv .venv
	.venv/Scripts/pip install -r requirements.txt

run:
	.venv/Scripts/uvicorn main:app --reload

test:
	.venv/Scripts/pytest -v

coverage:
	.venv/Scripts/pytest --cov=slink_platform --cov-report=term-missing --cov-report=html

# NFR/Performance tests (values from README)
# Tip: adjust env vars on the command if needed.
nfr:
	RUN_NFR=1 NFR_CONCURRENCY=8 NFR_REQUESTS=4000 NFR_TARGET_REDIRECT_QPS=800 NFR_TARGET_REDIRECT_P95_MS=5 .venv/Scripts/pytest tests/nfr -vv

# Switch to sequential strategy and run NFR (as in README)
nfr-sequential:
	SLINK_CODE_STRATEGY=sequential RUN_NFR=1 NFR_CONCURRENCY=8 NFR_REQUESTS=4000 NFR_TARGET_REDIRECT_QPS=800 NFR_TARGET_REDIRECT_P95_MS=5 .venv/Scripts/pytest tests/nfr -vv

# --- Docker (same commands as README) ---

docker-build:
	docker build -t slink-platform .

# Foreground, sequential strategy (exactly like README "Run" section, single line)
docker-run-seq:
	docker run --rm -p 8000:8000 -e SLINK_CODE_STRATEGY=sequential -e SLINK_SEQ_START=100000 --name slink slink-platform

# Deterministic strategy run (from README's “deterministic” example)
docker-run-det:
	docker run --rm -p 8000:8000 --name slink slink-platform

docker-logs:
	docker logs -f slink

docker-shell:
	docker exec -it slink sh

docker-stop:
	-docker rm -f slink

# --- Cleanup ---

clean:
	-docker rm -f slink
	-rm -rf .venv __pycache__ .pytest_cache htmlcov .mypy_cache
