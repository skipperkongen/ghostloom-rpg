.PHONY: help start stop restart build logs shell clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

start: ## Start the service
	docker compose up -d

stop: ## Stop the service
	docker compose down

restart: stop start ## Restart the service

build: ## Build the Docker image
	docker compose build

logs: ## View service logs
	docker compose logs -f api

shell: ## Open a shell in the running container
	docker compose exec api /bin/bash

clean: ## Stop and remove containers, networks, and volumes
	docker compose down -v

rebuild: clean build start ## Clean, rebuild, and start the service
