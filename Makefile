.DEFAULT_GOAL := help
.PHONY: help install test lint format clean all

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dev dependencies + pre-commit hooks
	pip install -e ".[dev]"
	pip install pre-commit
	pre-commit install
	@echo "✅ Ready to develop!"

test: ## Run tests with coverage
	pytest tests/ -v --tb=short --cov=denai --cov-report=term-missing --cov-fail-under=75

lint: ## Run linter checks (no auto-fix)
	ruff check denai/ tests/
	ruff format --check denai/ tests/

format: ## Auto-format code
	ruff check denai/ tests/ --fix
	ruff format denai/ tests/

clean: ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info .pytest_cache .ruff_cache htmlcov/ coverage.xml .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

all: lint test ## Run lint + tests (CI equivalent)
