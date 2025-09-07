.PHONY: help install test lint format type-check clean dev-install

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install -r requirements.txt

dev-install:  ## Install development dependencies
	pip install -e ".[dev]"
	pre-commit install

test:  ## Run tests
	pytest

test-contract:  ## Run contract tests only
	pytest tests/contract/ -v

test-integration:  ## Run integration tests only
	pytest tests/integration/ -v

test-unit:  ## Run unit tests only
	pytest tests/unit/ -v

lint:  ## Run linting
	ruff check src/ tests/
	black --check src/ tests/

format:  ## Format code
	black src/ tests/
	ruff check --fix src/ tests/

type-check:  ## Run type checking
	mypy src/

clean:  ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

check-all: lint type-check test  ## Run all checks