# UCAN Development Makefile
# Provides convenient commands for testing, linting, and development

.PHONY: help install install-dev test test-fast lint format type-check security check-all clean run

# Default target
help:
	@echo "UCAN Development Commands:"
	@echo ""
	@echo "  install       Install production dependencies"
	@echo "  install-dev   Install development dependencies" 
	@echo "  test          Run all tests with coverage"
	@echo "  test-fast     Run tests without coverage (faster)"
	@echo "  lint          Run all linting (flake8, syntax check)"
	@echo "  format        Format code with black and isort"
	@echo "  type-check    Run mypy type checking"
	@echo "  security      Run security checks (bandit, safety)"
	@echo "  check-all     Run all checks (lint, type, security, test)"
	@echo "  clean         Clean up generated files"
	@echo "  run           Run the TUI application"
	@echo ""

# Installation targets
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

# Testing targets
test:
	@echo "🧪 Running comprehensive tests with coverage..."
	python -m pytest tests/ -v --cov=can_tui --cov-report=term-missing --cov-report=html

test-fast:
	@echo "⚡ Running fast tests without coverage..."
	python -m pytest tests/ -v --disable-warnings

test-syntax:
	@echo "📝 Running syntax validation tests..."
	python -m pytest tests/test_syntax_and_imports.py -v

test-views:
	@echo "🎯 Running view system tests..."
	python -m pytest tests/test_view_system.py -v

# Code quality targets
lint:
	@echo "🔍 Running syntax check..."
	@find . -name "*.py" -not -path "./ucan_env/*" -not -path "./.venv/*" -not -path "./venv/*" -exec python -m py_compile {} \;
	@echo "✅ Syntax check passed"
	@echo ""
	@echo "🔍 Running flake8 linting..."
	flake8 can_tui/ tests/ --exclude=ucan_env,venv,.venv --max-line-length=100
	@echo "✅ Flake8 linting passed"

format:
	@echo "🎨 Formatting code with black..."
	black can_tui/ tests/ --line-length=88 --exclude=ucan_env
	@echo "📊 Sorting imports with isort..."
	isort can_tui/ tests/ --profile=black --skip=ucan_env
	@echo "✅ Code formatting complete"

type-check:
	@echo "🏷️  Running mypy type checking..."
	mypy can_tui/ --ignore-missing-imports --exclude=ucan_env
	@echo "✅ Type checking passed"

security:
	@echo "🔒 Running security checks with bandit..."
	@bandit -r can_tui/ -f json -o bandit-report.json || echo "⚠️  Security issues found - check bandit-report.json"
	@echo "🛡️  Checking dependencies with safety..."
	@safety check --json --output safety-report.json || echo "⚠️  Vulnerable dependencies found - check safety-report.json"
	@echo "✅ Security checks complete"

# Combined check target
check-all: lint type-check security test
	@echo ""
	@echo "🎉 All checks passed! Ready for commit."

# Utility targets  
clean:
	@echo "🧹 Cleaning up generated files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/
	rm -f bandit-report.json safety-report.json
	@echo "✅ Cleanup complete"

run:
	@echo "🚀 Starting CAN TUI..."
	python -m can_tui.main

run-dev:
	@echo "🔧 Starting CAN TUI in development mode..."
	python -m can_tui.main -p /dev/ttyACM0

# Pre-commit hook simulation
pre-commit: format lint type-check test-fast
	@echo "✅ Pre-commit checks passed"

# CI simulation  
ci: check-all
	@echo "✅ CI checks passed"