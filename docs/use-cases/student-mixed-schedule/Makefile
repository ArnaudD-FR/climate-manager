SLUG := student-mixed-schedule
PROJECT_ROOT := $(shell cd ../../.. && pwd)

.PHONY: screenshots

screenshots:
	docker run --rm --ipc=host \
		-v "$(PROJECT_ROOT):/app" \
		-e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
		-e OUTPUT_DIR=/app/docs/use-cases/$(SLUG)/screenshots \
		-e HARNESS_PATH=/docs/use-cases/student-mixed-schedule/harness.html \
		mcr.microsoft.com/playwright:v1.49.0-noble \
		bash -c "cd /app/docs && npm install --no-audit --no-fund 2>/dev/null \
		  && node screenshot.js"
