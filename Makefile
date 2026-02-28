# ──────────────────────────────────────────────────────────────
# MCP Sentinel — Project Makefile
# ──────────────────────────────────────────────────────────────
#
# Targets:
#   Testing & Quality    test, lint, typecheck, security, quality
#   Docker               docker-build, docker-push, ghcr-push
#   Release              release-dry, release, changelog
#   Utilities             clean, dev-install
#
# Prerequisites:
#   uv, docker, semgrep, snyk, python-semantic-release
# ──────────────────────────────────────────────────────────────

SHELL := /bin/bash
.DEFAULT_GOAL := help

# ── Load .env (if present) and export all variables ─────────
-include .env
export

# ── Project metadata (read from pyproject.toml) ─────────────
VERSION := $(shell python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])" 2>/dev/null || echo "0.0.0")
IMAGE_DOCKERHUB := diaz3618/mcp-sentinel
IMAGE_GHCR      := ghcr.io/diaz3618/mcp-sentinel
PLATFORMS        := linux/amd64,linux/arm64

# ── Semgrep rule packs tailored to this project ─────────────
SEMGREP_PACKS := p/python p/security-audit p/secrets p/dockerfile

# ── Help ────────────────────────────────────────────────────
.PHONY: help
help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ══════════════════════════════════════════════════════════════
# Testing & Quality
# ══════════════════════════════════════════════════════════════

.PHONY: test
test: ## Run pytest suite
	uv run pytest tests/ -q

.PHONY: lint
lint: ## Run ruff linter
	uv run ruff check mcp_sentinel/ tests/

.PHONY: typecheck
typecheck: ## Run mypy type checker
	uv run mypy mcp_sentinel/

.PHONY: semgrep
semgrep: ## Run semgrep (custom + registry rules)
	semgrep scan --config .semgrep.yml $(addprefix --config ,$(SEMGREP_PACKS)) mcp_sentinel/

.PHONY: snyk
snyk: ## Run Snyk code scan (SAST)
	snyk code test --severity-threshold=medium

.PHONY: snyk-sca
snyk-sca: ## Run Snyk SCA scan (dependency vulnerabilities)
	uv export --format requirements-txt --no-hashes --no-emit-project 2>/dev/null | \
		grep -v '^\s*#' | grep -v '^\s*$$' | sed 's/ ;.*//' > .snyk-requirements.txt
	snyk test --file=.snyk-requirements.txt --package-manager=pip --severity-threshold=medium; \
		SCA_EXIT=$$?; rm -f .snyk-requirements.txt; \
		if [ $$SCA_EXIT -ne 0 ]; then exit $$SCA_EXIT; fi

.PHONY: security
security: semgrep snyk ## Run all security scans (semgrep + snyk)

.PHONY: quality
quality: lint typecheck test security ## Full quality gate (lint + types + tests + security)

# ══════════════════════════════════════════════════════════════
# Docker — Build
# ══════════════════════════════════════════════════════════════

.PHONY: docker-build
docker-build: ## Build Docker image (local, current arch)
	docker build -t $(IMAGE_DOCKERHUB):$(VERSION) -t $(IMAGE_DOCKERHUB):latest .
	@echo "Built $(IMAGE_DOCKERHUB):$(VERSION)"

# ══════════════════════════════════════════════════════════════
# Docker — Publish to Docker Hub
# ══════════════════════════════════════════════════════════════

.PHONY: docker-push
docker-push: ## Build multi-arch and push to Docker Hub
	docker buildx build \
		--platform $(PLATFORMS) \
		--tag $(IMAGE_DOCKERHUB):$(VERSION) \
		--tag $(IMAGE_DOCKERHUB):latest \
		--push .
	@echo "Pushed $(IMAGE_DOCKERHUB):$(VERSION) + latest"

# ══════════════════════════════════════════════════════════════
# Docker — Publish to GHCR
# ══════════════════════════════════════════════════════════════

.PHONY: ghcr-push
ghcr-push: ## Build multi-arch and push to GHCR
	docker buildx build \
		--platform $(PLATFORMS) \
		--tag $(IMAGE_GHCR):$(VERSION) \
		--tag $(IMAGE_GHCR):latest \
		--push .
	@echo "Pushed $(IMAGE_GHCR):$(VERSION) + latest"

# ══════════════════════════════════════════════════════════════
# Release — Versioning & Changelog (python-semantic-release)
# ══════════════════════════════════════════════════════════════

.PHONY: changelog
changelog: ## Generate/update CHANGELOG.md from commit history
	semantic-release changelog

.PHONY: release-dry
release-dry: ## Preview next version without making changes
	semantic-release version --print
	@echo "---"
	semantic-release --noop version

.PHONY: release
release: quality ## Cut a release (bump version, tag, changelog, push)
	semantic-release version
	@echo "Release complete. Version: $$(semantic-release version --print-last-released)"

.PHONY: publish
publish: release docker-push ghcr-push ## Full release + publish to both registries

# ══════════════════════════════════════════════════════════════
# Utilities
# ══════════════════════════════════════════════════════════════

.PHONY: dev-install
dev-install: ## Install project + dev dependencies via uv
	uv sync --group dev

.PHONY: clean
clean: ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info mcp_sentinel.egg-info/
	find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -not -path './.venv/*' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -not -path './.venv/*' -exec rm -rf {} + 2>/dev/null || true
