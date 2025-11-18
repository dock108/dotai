PNPM ?= pnpm
UVX ?= uvx

.PHONY: lint test dev fmt fmt-js fmt-py

lint:
	$(PNPM) lint
	$(UVX) ruff check services packages
	$(UVX) black --check services packages

test:
	$(PNPM) test
	$(UVX) pytest || true

dev:
	$(PNPM) dev

fmt: fmt-js fmt-py

fmt-js:
	$(PNPM) format:write

fmt-py:
	$(UVX) black services packages

