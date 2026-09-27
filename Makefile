PY := venv/bin/python

.PHONY: install test test-web test-e2e test-harness test-mongo suite suite-deterministic latency contracts contracts-check migrate images images-restore icons assets-push assets-pull verify dev-api dev-web

PER_CATEGORY ?= 15

WORKERS ?= 3
LLM     ?=
MODEL   ?=
ASSETS  ?=

install:
	python3 -m venv orchestrator/venv
	cd orchestrator && $(PY) -m pip install -r requirements.txt
	$(MAKE) icons

test:
	cd orchestrator && $(PY) -m pytest tests -q

test-web:
	cd frontend && npm test

test-e2e:
	cd frontend && E2E_SITE=$(or $(E2E_SITE),http://localhost:3001) E2E_API=$(or $(E2E_API),http://localhost:8001) npm run e2e

test-harness:
	cd orchestrator && $(PY) -m pytest tests/harness -q

test-mongo:
	cd orchestrator && $(PY) -m pytest tests/mongo -q

suite-deterministic:
	cd orchestrator && MLP_IMAGES=stub $(PY) -m tatl --adapter mlp_adapter:DeterministicAdapter --workers $(WORKERS)$(if $(SELECT), -k $(SELECT),) --stage outcome --no-html
	cd orchestrator && MLP_IMAGES=stub $(PY) -m tatl --adapter mlp_adapter:DeterministicAdapter --workers $(WORKERS)$(if $(SELECT), -k $(SELECT),) --stage path --no-html

contracts:
	cd orchestrator && MLP_LLM=stub $(PY) scripts/export_contracts.py
	cd frontend && npm run contracts

contracts-check:
	cd orchestrator && MLP_LLM=stub $(PY) scripts/export_contracts.py --check
	cd frontend && npm run contracts:check

migrate:
	cd orchestrator && $(PY) scripts/migrate_pages.py $(if $(ADOPT), --adopt $(ADOPT),)$(if $(DRY), --dry-run,)

suite:
	cd orchestrator && $(if $(LLM),MLP_LLM=$(LLM) ,)$(if $(MODEL),MLP_LLM_MODEL=$(MODEL) ,)$(PY) -m tatl --workers $(WORKERS)$(if $(SELECT), -k $(SELECT),)$(if $(STAGE), --stage $(STAGE),)$(if $(SERVE), --serve,)

latency:
	cd orchestrator && $(if $(LLM),MLP_LLM=$(LLM) ,)$(if $(MODEL),MLP_LLM_MODEL=$(MODEL) ,)$(PY) scripts/latency_bench.py --repeats $(or $(REPEATS),3)$(if $(SELECT), -k $(SELECT),)

images:
	cd orchestrator && $(PY) scripts/fetch_library.py --per-category $(PER_CATEGORY)
	cd orchestrator && $(PY) scripts/embed_library.py

images-restore:
	cd orchestrator && $(PY) scripts/fetch_library.py --from-metadata
	cd orchestrator && $(PY) scripts/embed_library.py

icons:
	cd orchestrator && $(PY) scripts/fetch_icons.py $(ICON_ARGS)

assets-push:
	aws s3 sync frontend/public/images/library $(ASSETS)/images/library
	aws s3 sync frontend/public/icons $(ASSETS)/icons
	aws s3 sync orchestrator/image_library $(ASSETS)/image_library --exclude "*" --include "index.json" --include "embeddings.npy"

assets-pull:
	aws s3 sync $(ASSETS)/images/library frontend/public/images/library
	aws s3 sync $(ASSETS)/icons frontend/public/icons
	aws s3 sync $(ASSETS)/image_library orchestrator/image_library

verify: test test-web contracts-check
	cd frontend && npx tsc --noEmit && npm run lint

dev-api:
	cd orchestrator && $(PY) -m uvicorn main:app --reload --port 8000

dev-web:
	cd frontend && npm run dev
