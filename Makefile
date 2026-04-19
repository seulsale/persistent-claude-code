.PHONY: run test lint install uninstall

run:
	python3 -m persistent_claude_code

test:
	python3 -m pytest

lint:
	python3 -m ruff check

install:
	./install.sh

uninstall:
	./uninstall.sh
