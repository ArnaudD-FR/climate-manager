-include Makefile.local
HA_USER ?= root
HA_HOST ?= homeassistant.local
HA_COMPONENT_DIR = /config/custom_components/climate_manager
SRC_DIR = custom_components/climate_manager
VERSION := $(shell python3 -c "import json; print(json.load(open('$(SRC_DIR)/manifest.json'))['version'])")

.PHONY: build deploy test lint logs screenshots use-case-screenshots release

build:
	cd frontend && npm install --no-audit --no-fund && npm run build

deploy: build
	ssh $(HA_USER)@$(HA_HOST) "mkdir -p $(HA_COMPONENT_DIR)"
	tar -C $(SRC_DIR) \
		--exclude='__pycache__' \
		--exclude='*.pyc' --exclude='*.pyo' \
		-czf - . | ssh $(HA_USER)@$(HA_HOST) "tar -C $(HA_COMPONENT_DIR) -xzf -"
	ssh $(HA_USER)@$(HA_HOST) "ha core restart"

release: build
	@mkdir -p dist
	@rm -f dist/climate_manager.zip
	cd custom_components && zip -r ../dist/climate_manager.zip climate_manager/ \
		-x "climate_manager/__pycache__/*" \
		-x "climate_manager/*/__pycache__/*" \
		-x "*.pyc" -x "*.pyo" -x "*.map" -x "*/.gitignore"
	@echo "Release archive: dist/climate_manager.zip (v$(VERSION))"

test:
	.venv/bin/python -m pytest tests/ -v

lint:
	pre-commit run --all-files

logs:
	ssh $(HA_USER)@$(HA_HOST) "ha core logs -f"

screenshots: build
	@mkdir -p docs/screenshots
	docker run --rm --ipc=host \
		-v "$$(pwd):/app" \
		-e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
		mcr.microsoft.com/playwright:v1.49.0-noble \
		bash -c "cd /app/docs && npm install --no-audit --no-fund 2>/dev/null && node screenshot.js"
	$(MAKE) use-case-screenshots

use-case-screenshots:
	@for dir in docs/use-cases/*/; do \
		if [ -f "$$dir/Makefile" ]; then \
			echo "--- $$dir ---"; \
			$(MAKE) -C "$$dir" screenshots; \
		fi \
	done
