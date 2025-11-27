SHELL := /bin/sh
.DEFAULT_GOAL := help

# Environment and configuration
ENV ?= local
PYTHON ?= python3
UV ?= uv
SERVICE ?=

# Build configuration
BUILD_SPEC ?= build.spec
BUILD_DIR ?= dist
BUILD_MODE ?= onefile

# Development server options
DEV_OPTS ?=

# Test options
TEST_PATH ?= tests
TEST_OPTS ?=
COVERAGE_OPTS ?= --cov=app --cov-report=html --cov-report=term

# Lint and format options
LINT_OPTS ?=
FORMAT_OPTS ?=
PRE_COMMIT_OPTS ?=

# Detect package manager
ifeq ($(shell command -v uv >/dev/null 2>&1 && echo yes),yes)
  PKG_MANAGER := uv
  INSTALL_CMD := uv sync --active
  RUN_CMD := uv run --active
else
  PKG_MANAGER := pip
  INSTALL_CMD := pip install -e .
  RUN_CMD := python -m
endif

HELP_ENV := $(ENV) (using $(PKG_MANAGER))

.PHONY: help install dev run build clean lint format test pre-commit generate_secret_key shell

help:
	@printf "Environment: %s\\n" "$(HELP_ENV)"
	@printf "Package manager: %s\\n" "$(PKG_MANAGER)"
	@printf "Available targets:\\n"
	@printf "  make install                       # Install dependencies\\n"
	@printf "  make dev                           # Install dev dependencies\\n"
	@printf "  make run                           # Run the application\\n"
	@printf "  make build [BUILD_MODE=onefile]    # Build executable (onefile/onedir)\\n"
	@printf "  make clean                         # Clean build artifacts\\n"
	@printf "  make lint                          # Run linters (ruff, mypy)\\n"
	@printf "  make format                        # Format code (ruff, black, isort)\\n"
	@printf "  make test [TEST_PATH=]             # Run tests with pytest\\n"
	@printf "  make pre-commit                    # Run pre-commit hooks\\n"
	@printf "  make generate_secret_key           # Generate a Base64 URL-safe secret key\\n"
	@printf "  make shell                         # Open Python shell with app context\\n"
	@printf "\\n"
	@printf "Override options: DEV_OPTS, TEST_OPTS, LINT_OPTS, FORMAT_OPTS\\n"

install:
	@if [ "$(PKG_MANAGER)" = "uv" ]; then \
		echo "Installing dependencies with uv..."; \
		uv sync --no-dev; \
	else \
		echo "Installing dependencies with pip..."; \
		pip install -e .; \
	fi
	@if [ ! -f .env ]; then \
		echo "Creating .env from template..."; \
		cp .env.template .env; \
	else \
		echo ".env file already exists, skipping..."; \
	fi

dev:
	@if [ "$(PKG_MANAGER)" = "uv" ]; then \
		echo "Installing dev dependencies with uv..."; \
		uv sync --group dev; \
	else \
		echo "Installing dev dependencies with pip..."; \
		pip install -e ".[dev]"; \
	fi
	@if [ ! -f .env ]; then \
		echo "Creating .env from template..."; \
		cp .env.template .env; \
	fi
	@if command -v pre-commit >/dev/null 2>&1; then \
		echo "Installing pre-commit hooks..."; \
		pre-commit install; \
	fi

run:
	@echo "Running application..."
	@$(RUN_CMD) fco $(DEV_OPTS)

build:
	@if [ "$(BUILD_MODE)" = "onedir" ]; then \
		echo "Building onedir executable..."; \
		$(RUN_CMD) pyinstaller build_onedir.spec $(BUILD_OPTS); \
	else \
		echo "Building onefile executable..."; \
		$(RUN_CMD) pyinstaller $(BUILD_SPEC) $(BUILD_OPTS); \
	fi
	@echo "Build complete. Output in $(BUILD_DIR)/"

clean:
	@echo "Cleaning build artifacts..."
	@rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .ruff_cache __pycache__
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Clean complete."

lint:
	@echo "Running linters..."
	@if [ -f ./scripts/lint.sh ]; then \
		bash ./scripts/lint.sh $(LINT_OPTS); \
	else \
		echo "Running ruff check..."; \
		$(RUN_CMD) ruff check app/ $(LINT_OPTS); \
		echo "Running mypy..."; \
		$(RUN_CMD) mypy app/ $(LINT_OPTS); \
	fi

format:
	@echo "Formatting code..."
	@if [ -f ./scripts/format.sh ]; then \
		bash ./scripts/format.sh $(FORMAT_OPTS); \
	else \
		echo "Running ruff format..."; \
		$(RUN_CMD) ruff format app/ $(FORMAT_OPTS); \
		echo "Running ruff check --fix..."; \
		$(RUN_CMD) ruff check --fix app/ $(FORMAT_OPTS); \
		echo "Running isort..."; \
		$(RUN_CMD) isort app/ $(FORMAT_OPTS); \
	fi

test:
	@echo "Running tests..."
	@$(RUN_CMD) pytest $(TEST_PATH) $(COVERAGE_OPTS) $(TEST_OPTS)

pre-commit:
	@echo "Running pre-commit hooks..."
	@pre-commit run --all-files $(PRE_COMMIT_OPTS)

generate_secret_key:
	@python -c "import os, base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"

shell:
	@echo "Opening Python shell..."
	@$(RUN_CMD) python
