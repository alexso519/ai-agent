# =============================================================================
# CrewAI Enterprise Control Center — Makefile
# Phase 0: Monorepo Foundation
# =============================================================================

.PHONY: help install dev build lint type-check test clean docker-build docker-up docker-down

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies
	pnpm install

dev: ## Start development servers
	pnpm dev

build: ## Build all packages and apps
	pnpm build

lint: ## Lint all code
	pnpm lint

type-check: ## Run TypeScript type checking
	pnpm type-check

test: ## Run all tests
	pnpm test

clean: ## Clean all build artifacts
	pnpm clean

format: ## Format all code with Prettier
	pnpm format

format-check: ## Check code formatting
	pnpm format:check

docker-build: ## Build all Docker images
	docker compose -f infra/docker/docker-compose.yml build

docker-up: ## Start development Docker stack
	docker compose -f infra/docker/docker-compose.yml up -d

docker-down: ## Stop development Docker stack
	docker compose -f infra/docker/docker-compose.yml down

docker-logs: ## View Docker logs
	docker compose -f infra/docker/docker-compose.yml logs -f

setup: install ## Full project setup
	cp -n .env.example .env || true
	@echo "Project setup complete. Edit .env with your configuration."