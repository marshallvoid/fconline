STANDALONE_ARGS = -f compose/stack.yml
KNOWN_TARGETS = help install start stop destroy restart reset logs ps lint format exec generate_secret_key
ARGS := $(filter-out $(KNOWN_TARGETS),$(MAKECMDGOALS))
EXEC := /bin/bash

# turn ARGS into do-nothing targets
ifneq ($(ARGS),$(MAKECMDGOALS))
$(eval $(ARGS):;@:)
endif

.PHONY: help
help: ## Show this help information
	@echo "Please use 'make <target>' where <target> is one of the following commands.\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' Makefile | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo "\nCheck the Makefile to know exactly what each target is doing."

.PHONY: install
install: ## Bootstrapping the stack
	@cp -i .env.example .env || echo ".env file already exists, skipping..."

.PHONY: start
start:  ## Start the stack
	@docker compose ${STANDALONE_ARGS} up -d
	@docker compose ${STANDALONE_ARGS} ps

.PHONY: stop
stop:  ## Stop the stack, keep resources (volumes, networks,...)
	@docker compose ${STANDALONE_ARGS} stop

.PHONY: destroy
destroy:  ## Stop the stack and purge resources (WARN: data will be lost after this)
	@docker compose ${STANDALONE_ARGS} down $(ARGS) -v

.PHONY: ## Restart the stack without purging data (`stop start`)
restart: stop start $(ARGS)

.PHONY: ## Restart the stack and purge the data as well (`destroy start`)
reset: destroy start

.PHONY: logs
logs: ## make logs [service-name]; leave service empty to fetch all servide log
	@docker compose ${STANDALONE_ARGS} logs $(ARGS) -f

.PHONY: ps
ps: ## List out all Docker containers of services
	@docker compose ${STANDALONE_ARGS} ps

.PHONY: lint
lint: ## Lint the source code
	@bash ./scripts/lint.sh

.PHONY: format
format: ## Format the source code
	@bash ./scripts/format.sh

.PHONY: exec
exec: ## make exec <service-name> <executable>. E.g: make exec api /bin/bash
	@docker compose ${STANDALONE_ARGS} $(ARGS)

.PHONY: generate_secret_key
generate_secret_key: ## Generate a Base64 URL-safe secret key
	@python -c "import os, base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
