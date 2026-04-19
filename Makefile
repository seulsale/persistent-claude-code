.PHONY: run test lint install uninstall

run:
	PYTHONPATH=src python3 -m persistent_claude_code

test:
	.venv/bin/python -m pytest

lint:
	.venv/bin/python -m ruff check

install:
	./install.sh

uninstall:
	./uninstall.sh
