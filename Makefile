-include Makefile.local
HA_USER ?= root
HA_HOST ?= homeassistant.local
HA_COMPONENT_DIR = /config/custom_components/climate_manager
SRC_DIR = custom_components/climate_manager

.PHONY: build deploy test logs

build:
	cd frontend && npm install --no-audit --no-fund && npm run build

deploy: build
	ssh $(HA_USER)@$(HA_HOST) "mkdir -p $(HA_COMPONENT_DIR)"
	scp -r $(SRC_DIR)/. $(HA_USER)@$(HA_HOST):$(HA_COMPONENT_DIR)/
	ssh $(HA_USER)@$(HA_HOST) "ha core restart"

test:
	.venv/bin/python -m pytest tests/ -v

logs:
	ssh $(HA_USER)@$(HA_HOST) "ha core logs -f"
