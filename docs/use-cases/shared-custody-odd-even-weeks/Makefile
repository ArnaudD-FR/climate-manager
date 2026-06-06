SLUG := shared-custody-odd-even-weeks
PROJECT_ROOT := $(shell cd ../../.. && pwd)

.PHONY: screenshots

# Renders from the generated scenario.json (see `make use-case-data`). The
# shared harness reads it via ?scenario=, and screenshot.js pins the browser
# clock to scenario.now (SCENARIO_JSON) so the view matches the coordinator
# status exactly.
screenshots:
	docker run --rm --ipc=host \
		-v "$(PROJECT_ROOT):/app" \
		-e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
		-e OUTPUT_DIR=/app/docs/use-cases/$(SLUG)/screenshots \
		-e HARNESS_PATH="/docs/use-cases/_harness.html?scenario=/docs/use-cases/$(SLUG)/scenario.json" \
		-e SCENARIO_JSON=/app/docs/use-cases/$(SLUG)/scenario.json \
		mcr.microsoft.com/playwright:v1.49.0-noble \
		bash -c "cd /app/docs && npm install --no-audit --no-fund 2>/dev/null \
		  && node screenshot.js"
