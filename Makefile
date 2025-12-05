# Dock108 Development Commands
# Run these from the repo root directory

COMPOSE_FILE := infra/docker-compose.yml
ENV_FILE := .env

.PHONY: up down restart logs ps build clean

# Start all services
up:
	docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) up -d

# Start specific service(s) - usage: make up-svc SVC="theory-engine-api scraper-worker"
up-svc:
	docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) up -d $(SVC)

# Stop all services
down:
	docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) down

# Restart all services
restart: down up

# View logs (all services)
logs:
	docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) logs -f

# View logs for specific service - usage: make logs-svc SVC=scraper-worker
logs-svc:
	docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) logs -f $(SVC)

# Show running containers
ps:
	docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) ps

# Rebuild images
build:
	docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) build

# Rebuild specific service - usage: make build-svc SVC=theory-engine-api
build-svc:
	docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) build $(SVC)

# Stop and remove containers, networks, volumes
clean:
	docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) down -v --remove-orphans

# Rebuild and restart a specific service
rebuild-svc:
	docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) up -d --build $(SVC)
