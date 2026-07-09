.PHONY: help start stop restart build logs shell clean migrate logs-all

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

start: ## Start all services
	docker compose up -d --build

stop: ## Stop all services
	docker compose down

restart: stop start ## Restart all services

build: ## Build Docker images
	docker compose build

logs: ## View API service logs
	docker compose logs -f api

logs-all: ## View all service logs
	docker compose logs -f

shell: ## Open a shell in the running API container
	docker compose exec api /bin/bash

migrate: ## Run database migrations
	docker compose run --rm migrate

clean: ## Stop and remove containers, networks, and volumes
	docker compose down -v

rebuild: clean start ## Clean, rebuild, and start all services
