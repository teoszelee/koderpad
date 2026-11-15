.PHONY: help init dev test check format update-hooks clean db
.DEFAULT: help
-include .env

PYTHON=python3.11
# Existing data directories must use their original Postgres major version.
POSTGRES_VERSION ?= $(shell cat db/PG_VERSION 2>/dev/null || echo 16)

help: ## Display this help message
	@echo "Please use \`make <target>\` where <target> is one of"
	@awk -F ':.*?## ' '/^[a-zA-Z]/ && NF==2 {printf "\033[36m  %-25s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

clean: ## Remove virtual environment and cache
	rm -rf .venv
	rm -rf .ruff_cache
	rm -rf .pytest_cache
	rm .coverage

init: ## Initialize the virtual environment and install dependencies
	uv sync
	uv tool run pre-commit install

check: ## Run lint, format, type, and regression checks without rewriting files
	uv run --locked ruff check src tests
	uv run --locked ruff format --check src tests
	uv run --locked ty check src tests
	uv run --locked pytest

format: ## Apply Ruff import sorting, lint fixes, and formatting
	uv run --locked ruff check --select I --fix src tests
	uv run --locked ruff check --fix src tests
	uv run --locked ruff format src tests

update-hooks: ## Update pre-commit hook versions
	uv tool run pre-commit autoupdate

test: ## Run regression tests (Postgres integration requires a disposable database)
	uv run --locked pytest

dev: ## Run the app
	uv run streamlit run src/main.py

db: ## Run the local Postgres database, preserving its existing major version
	docker run -d --rm \
	-p 5432:5432 \
	--name koderpad-db  \
	-v "$(PWD)/db:/var/lib/postgresql/data" \
	-e POSTGRES_USER=postgres \
	-e POSTGRES_PASSWORD=postgres \
	-e POSTGRES_DB=postgres \
	-e TZ=UTC \
	postgres:$(POSTGRES_VERSION)
