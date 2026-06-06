SLUG := student-mixed-schedule
PROJECT_ROOT := $(shell cd ../../.. && pwd)

.PHONY: screenshots

# Renders one capture per variant scenario.<id>.json (see `make
# use-case-data`). For each variant the shared harness reads it via ?scenario=
# and screenshot.js pins the browser clock to that variant's moment, capturing
# overview-<id>.png + rooms-<id>.png. The "present" variant also captures the
# configuration screenshots (persons + per-zone schedules) via CAPTURE_CONFIG.
screenshots:
	@for json in scenario.*.json; do \
		id=$$(basename "$$json" .json); id=$${id#scenario.}; \
		cfg=0; [ "$$id" = "present" ] && cfg=1; \
		echo "  variant $$id (config=$$cfg)"; \
		docker run --rm --ipc=host \
			-v "$(PROJECT_ROOT):/app" \
			-e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
			-e OUTPUT_DIR=/app/docs/use-cases/$(SLUG)/screenshots \
			-e HARNESS_PATH="/docs/use-cases/_harness.html?scenario=/docs/use-cases/$(SLUG)/$$json" \
			-e SCENARIO_JSON=/app/docs/use-cases/$(SLUG)/$$json \
			-e VARIANT_ID=$$id \
			-e CAPTURE_CONFIG=$$cfg \
			mcr.microsoft.com/playwright:v1.49.0-noble \
			bash -c "cd /app/docs && npm install --no-audit --no-fund 2>/dev/null \
			  && node screenshot.js"; \
	done
