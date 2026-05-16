HA_USER ?= root
HA_HOST ?= homeassistant.local
HA_COMPONENT_DIR = /config/custom_components/climate_manager
SRC_DIR = custom_components/climate_manager

.PHONY: deploy test logs

deploy:
	rsync -av --delete $(SRC_DIR)/ $(HA_USER)@$(HA_HOST):$(HA_COMPONENT_DIR)/
	ssh $(HA_USER)@$(HA_HOST) "ha core restart"

test:
	.venv/bin/python -m pytest tests/ -v

logs:
	ssh $(HA_USER)@$(HA_HOST) "ha core logs -f"
