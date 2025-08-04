.PHONY: test test-unit test-integration test-shell test-coverage install clean help

# Default target
all: test

# Install dependencies
install:
	pip install -e .
	pip install -r requirements.txt

# Run all tests
test: test-unit test-integration test-shell

# Run unit tests only
test-unit:
	python -m pytest tests/ -m "unit or not (integration or cli or database)"

# Run integration tests
test-integration:
	python -m pytest tests/ -m integration

# Run CLI tests
test-cli:
	python -m pytest tests/ -m cli

# Run database tests
test-database:
	python -m pytest tests/ -m database

# Run shell tests
test-shell:
	bash tests/test_shell.sh

# Run with coverage
test-coverage:
	python -m pytest tests/ --cov=fin --cov-report=term-missing --cov-report=html:htmlcov

# Run performance tests
test-performance:
	python tests/run_tests.py --performance

# Run comprehensive test suite
test-all:
	python tests/run_tests.py --type all --shell --performance --coverage

# Quick test (unit tests only)
test-quick:
	python -m pytest tests/test_database.py tests/test_cli.py -v

# Clean up
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf .coverage

# Show help
help:
	@echo "Available targets:"
	@echo "  install        - Install dependencies"
	@echo "  test           - Run all tests"
	@echo "  test-unit      - Run unit tests only"
	@echo "  test-integration - Run integration tests"
	@echo "  test-cli       - Run CLI tests"
	@echo "  test-database  - Run database tests"
	@echo "  test-shell     - Run shell tests"
	@echo "  test-coverage  - Run tests with coverage"
	@echo "  test-performance - Run performance tests"
	@echo "  test-all       - Run comprehensive test suite"
	@echo "  test-quick     - Run quick tests only"
	@echo "  clean          - Clean up generated files"
	@echo "  help           - Show this help" 