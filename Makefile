.PHONY: help build up down restart logs logs-cron logs-app shell poll reset-state clean

help:
	@echo "Station 95 GroupMe Poller - Docker Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make build       Build the Docker image"
	@echo "  make up          Start the poller container"
	@echo ""
	@echo "Control:"
	@echo "  make down        Stop and remove containers"
	@echo "  make restart     Restart the poller"
	@echo ""
	@echo "Monitoring:"
	@echo "  make logs        View all logs (follow mode)"
	@echo "  make logs-cron   View cron execution logs"
	@echo "  make logs-app    View application logs"
	@echo "  make status      Check container status"
	@echo ""
	@echo "Operations:"
	@echo "  make shell       Open shell in container"
	@echo "  make poll        Trigger manual poll"
	@echo "  make reset-state Delete state file (reprocess messages)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean       Remove containers, images, and volumes"

build:
	docker-compose build

up:
	docker-compose up -d
	@echo ""
	@echo "✓ Poller is running!"
	@echo "View logs: make logs"
	@echo "Check status: make status"

down:
	docker-compose down

restart:
	docker-compose restart
	@echo "✓ Poller restarted"

logs:
	docker-compose logs -f

logs-cron:
	docker-compose exec groupme-poller tail -f /app/logs/cron.log

logs-app:
	@if [ -f logs/station95chatbot.log ]; then \
		tail -f logs/station95chatbot.log; \
	else \
		echo "Log file not found. Container may not have run yet."; \
	fi

status:
	@echo "Container Status:"
	@docker-compose ps
	@echo ""
	@echo "Last Message ID:"
	@if [ -f data/last_message_id.txt ]; then \
		cat data/last_message_id.txt; \
	else \
		echo "Not set (no messages processed yet)"; \
	fi
	@echo ""
	@echo "Cron Status:"
	@docker-compose exec groupme-poller pgrep cron > /dev/null && echo "✓ Cron is running" || echo "✗ Cron is not running"

shell:
	docker-compose exec groupme-poller bash

poll:
	@echo "Running manual poll..."
	docker-compose exec groupme-poller python -m src.station95chatbot.poll_messages

reset-state:
	@echo "Resetting poller state..."
	@if [ -f data/last_message_id.txt ]; then \
		rm data/last_message_id.txt; \
		echo "✓ State file deleted"; \
	else \
		echo "No state file to delete"; \
	fi
	@echo "Restarting container..."
	@docker-compose restart
	@echo "✓ State reset complete"

clean:
	@echo "Warning: This will remove all containers, images, and volumes!"
	@read -p "Are you sure? (y/N) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		docker rmi station95chatbot-groupme-poller 2>/dev/null || true; \
		echo "✓ Cleanup complete"; \
	else \
		echo "Cancelled"; \
	fi

# Development helpers
dev-setup:
	@echo "Setting up development environment..."
	@if [ ! -f .env ]; then \
		cp .env.docker.example .env; \
		echo "✓ Created .env from template"; \
		echo "⚠ Edit .env with your credentials before running 'make up'"; \
	else \
		echo ".env already exists"; \
	fi

rebuild:
	docker-compose up -d --build
	@echo "✓ Rebuilt and restarted"
