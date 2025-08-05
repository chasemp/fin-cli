.PHONY: test test-cov test-fail-fast test-unit test-integration test-cli test-analytics lint clean install

# Default target
all: test

# Install dependencies
install:
	pip install -e .
	pip install pytest pytest-cov flake8 black isort pre-commit

# Run all tests
test:
	python -m pytest tests/ -v

# Run tests with coverage
test-cov:
	python -m pytest tests/ --cov=fincli --cov-report=html --cov-report=term-missing

# Run tests and fail fast
test-fail-fast:
	python -m pytest tests/ -x --tb=short

# Run specific test categories
test-unit:
	python -m pytest tests/ -m unit -v

test-integration:
	python -m pytest tests/ -m integration -v

test-cli:
	python -m pytest tests/ -m cli -v

test-analytics:
	python -m pytest tests/test_analytics.py -v

# Linting and formatting
lint:
	flake8 fincli/ tests/
	black --check fincli/ tests/
	isort --check-only fincli/ tests/

format:
	black fincli/ tests/
	isort fincli/ tests/

# Clean up
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -f ~/fin/tasks.db

# Install pre-commit hooks
install-hooks:
	pre-commit install

# Run pre-commit on all files
pre-commit:
	pre-commit run --all-files

# Development setup
dev-setup: install install-hooks
	@echo "Development environment setup complete!"
	@echo "Run 'make test' to run tests"
	@echo "Run 'make test-cov' to check coverage"

# Quick test run (for development)
quick-test:
	python -m pytest tests/ -x --tb=short --maxfail=3

# Test with coverage threshold
test-cov-threshold:
	python -m pytest tests/ --cov=fincli --cov-fail-under=90

# Help
help:
	@echo "Available commands:"
	@echo "  test              - Run all tests"
	@echo "  test-cov          - Run tests with coverage report"
	@echo "  test-fail-fast    - Run tests and stop on first failure"
	@echo "  test-unit         - Run unit tests only"
	@echo "  test-integration  - Run integration tests only"
	@echo "  test-cli          - Run CLI tests only"
	@echo "  test-analytics    - Run analytics tests only"
	@echo "  lint              - Run linting checks"
	@echo "  format            - Format code with black and isort"
	@echo "  clean             - Clean up cache and temporary files"
	@echo "  install-hooks     - Install pre-commit hooks"
	@echo "  pre-commit        - Run pre-commit on all files"
	@echo "  dev-setup         - Set up development environment"
	@echo "  quick-test        - Quick test run for development"
	@echo "  test-cov-threshold - Test with 90% coverage threshold" 