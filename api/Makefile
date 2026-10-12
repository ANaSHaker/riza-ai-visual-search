.PHONY: install dev test lint run docker-build docker-run index-sample

install:        ## runtime dependencies (downloads torch)
	pip install -r requirements.txt

dev:            ## test/lint dependencies only (no torch)
	pip install -r requirements-dev.txt

test:
	python -m pytest

lint:
	ruff check app scripts tests

run:            ## local dev server bound to localhost
	uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

docker-build:
	docker build -t visual-search-api .

docker-run:
	docker run --rm -p 127.0.0.1:8000:8000 --env-file .env -v vs-data:/data -v vs-models:/models visual-search-api

index-sample:   ## index the sample catalogue into a running API
	python -m scripts.index_catalog csv examples/catalog.sample.csv --api http://127.0.0.1:8000
