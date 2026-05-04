.PHONY: help setup test eval lint format check

help:
	@echo "Available commands:"
	@echo "  setup    Install dependencies and tools"
	@echo "  test     Run unit tests with pytest"
	@echo "  eval     Run the evaluation script locally"
	@echo "  lint     Run code linting with ruff"
	@echo "  format   Format code with ruff"
	@echo "  check    Run type checking with mypy"

setup:
	pip install -r requirements.txt ruff mypy

test:
	pytest tests/

eval:
	python src/eval_runner.py

lint:
	ruff check src tests

format:
	ruff format src tests
	ruff check --fix src tests

check:
	mypy src
