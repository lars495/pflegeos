SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE := docker compose -f infra/docker-compose.yml --env-file infra/.env
TODAY   := $(shell date +%Y-%m-%d)

# ─── Hilfe ────────────────────────────────────────────────────────────────
help:  ## Zeigt alle Targets
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ─── Setup & Boot ─────────────────────────────────────────────────────────
first-boot:  ## Erststart auf frischem VPS
	@test -f infra/.env || (echo "infra/.env fehlt — siehe infra/.env.example" && exit 1)
	$(COMPOSE) build
	$(COMPOSE) up -d db redis
	@echo "Warte auf DB/Redis health…"
	@for i in $$(seq 1 30); do \
	  $(COMPOSE) ps db redis 2>/dev/null | grep -c healthy | grep -q 2 && break; \
	  sleep 2; \
	done
	# alembic-Migration sobald erste Migrations-Dateien existieren
	@if [ -d apps/api/alembic/versions ] && ls apps/api/alembic/versions/*.py >/dev/null 2>&1; then \
	  $(COMPOSE) run --rm api alembic upgrade head; \
	else \
	  echo "Keine Migrations vorhanden — Agent wird sie anlegen."; \
	fi
	$(COMPOSE) up -d

tls:  ## Let's-Encrypt-Zertifikate (acme.sh, einmalig)
	@bash scripts/setup_tls.sh

install-cron:  ## Installiert tägliche und monatliche Cron-Jobs
	@bash scripts/install_cron.sh

# ─── Entwicklung ──────────────────────────────────────────────────────────
up:  ## Stack starten
	$(COMPOSE) up -d

down:  ## Stack stoppen
	$(COMPOSE) down

logs:  ## Live-Logs (alle Services)
	$(COMPOSE) logs -f --tail=100

ps:  ## Service-Status
	$(COMPOSE) ps

shell-api:  ## Shell in api-Container
	$(COMPOSE) exec api bash

shell-db:  ## psql in db-Container
	$(COMPOSE) exec db psql -U $${POSTGRES_USER} -d pflegeos

# ─── Tests & Qualität ─────────────────────────────────────────────────────
test:  ## Test-Suite (pytest + svelte-tests + compliance + a11y)
	$(COMPOSE) exec -T api pytest -q
	$(COMPOSE) exec -T care-app npm test --silent
	@$(MAKE) compliance-check
	@$(MAKE) a11y-check

compliance-check:  ## Prüft legal_requirements.yaml gegen Codebase
	python scripts/check_compliance.py

a11y-check:  ## WCAG-2.1-AA-Scan auf Care-App
	python scripts/check_a11y.py

lint:  ## Ruff + Prettier + ESLint
	$(COMPOSE) exec -T api ruff check .
	$(COMPOSE) exec -T care-app npm run lint --silent

# ─── Autonomer Agent ──────────────────────────────────────────────────────
daily-agent:  ## Manueller Trigger des täglichen Build-Cycles
	bash scripts/daily_agent.sh

legal-audit:  ## Manueller Trigger des KI-Juristen
	$(COMPOSE) exec -T api python scripts/legal_audit.py

process-contributions:  ## Bearbeitet inbox/ Community-Einreichungen
	$(COMPOSE) exec -T api python scripts/process_contributions.py

post-update:  ## Postet $(TODAY)-Update zu LinkedIn + X
	$(COMPOSE) exec -T api python scripts/post_update.py --date $(TODAY)

# ─── Deploy ───────────────────────────────────────────────────────────────
deploy:  ## Rolling Deploy mit Health-Check und Auto-Rollback
	@bash scripts/deploy.sh

backup:  ## DB-Backup → verschlüsselt nach Hetzner Storage Box
	@bash scripts/backup.sh

# ─── Budget ───────────────────────────────────────────────────────────────
budget:  ## Aktueller LLM-Verbrauch heute
	$(COMPOSE) exec -T api python -m packages.llm.budget_guard status
