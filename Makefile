# Makefile for Centuries Mutual Home App

.PHONY: help build up down logs clean test lint format install dev

# Default target
help:
	@echo "Centuries Mutual Home App - Available Commands:"
	@echo ""
	@echo "  build     - Build Docker images"
	@echo "  up        - Start all services"
	@echo "  down      - Stop all services"
	@echo "  logs      - View application logs"
	@echo "  clean     - Clean up containers and volumes"
	@echo "  test      - Run tests"
	@echo "  lint      - Run linting checks"
	@echo "  format    - Format code"
	@echo "  install   - Install Python dependencies"
	@echo "  dev       - Start development server"
	@echo "  health    - Check application health"
	@echo "  shell     - Open shell in app container"
	@echo "  db-shell  - Open database shell"
	@echo "  backup    - Backup database"
	@echo "  restore   - Restore database"

# Docker commands
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f app

logs-all:
	docker-compose logs -f

clean:
	docker-compose down -v --remove-orphans
	docker system prune -f

# Development commands
install:
	pip install -r requirements.txt

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v

lint:
	flake8 app/
	mypy app/

format:
	black app/
	isort app/

# Utility commands
health:
	curl -f http://localhost:8000/health || echo "Health check failed"

shell:
	docker-compose exec app /bin/bash

db-shell:
	docker-compose exec postgres psql -U postgres -d notifications_db

backup:
	docker-compose exec postgres pg_dump -U postgres notifications_db > backup_$(shell date +%Y%m%d_%H%M%S).sql

restore:
	@echo "Usage: make restore FILE=backup_file.sql"
	@if [ -z "$(FILE)" ]; then echo "Please specify FILE=backup_file.sql"; exit 1; fi
	docker-compose exec -T postgres psql -U postgres -d notifications_db < $(FILE)

# SSL certificate generation
ssl:
	mkdir -p ssl
	openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
		-keyout ssl/key.pem -out ssl/cert.pem \
		-subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Database migrations
migrate:
	docker-compose exec app alembic upgrade head

migrate-create:
	@echo "Usage: make migrate-create MESSAGE=migration_message"
	@if [ -z "$(MESSAGE)" ]; then echo "Please specify MESSAGE=migration_message"; exit 1; fi
	docker-compose exec app alembic revision --autogenerate -m "$(MESSAGE)"

# Production deployment
deploy:
	docker-compose -f docker-compose.yml up -d --build

scale:
	@echo "Usage: make scale SERVICE=service_name REPLICAS=number"
	@if [ -z "$(SERVICE)" ] || [ -z "$(REPLICAS)" ]; then echo "Please specify SERVICE and REPLICAS"; exit 1; fi
	docker-compose up -d --scale $(SERVICE)=$(REPLICAS)

# Monitoring
stats:
	docker stats

top:
	docker-compose top

# Environment setup
env:
	cp config.env.example .env
	@echo "Please edit .env with your configuration"

# Quick start
quickstart: env ssl build up
	@echo "Application is starting up..."
	@echo "Waiting for services to be ready..."
	@sleep 10
	@make health
	@echo ""
	@echo "Application is ready!"
	@echo "API Documentation: http://localhost:8000/docs"
	@echo "Health Check: http://localhost:8000/health"
	@echo "RabbitMQ Management: http://localhost:15672 (guest/guest)"
