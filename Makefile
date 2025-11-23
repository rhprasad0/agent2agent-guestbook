.PHONY: help build scan test run clean

IMAGE_NAME ?= guestbook
IMAGE_TAG ?= local
FULL_IMAGE = $(IMAGE_NAME):$(IMAGE_TAG)

help: ## Show this help message
	@echo "Guestbook Development Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker image locally
	@echo "🔨 Building $(FULL_IMAGE)..."
	docker build -t $(FULL_IMAGE) .
	@echo "✅ Build complete"

scan: build ## Build and scan image with Trivy
	@echo "🔍 Scanning $(FULL_IMAGE) for vulnerabilities..."
	./scripts/scan-image.sh $(FULL_IMAGE)

test: ## Run application tests
	@echo "🧪 Running tests..."
	python -m pytest tests/ -v

run: ## Run application locally (requires .env)
	@echo "🚀 Starting application..."
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-docker: build ## Run application in Docker
	@echo "🐳 Running $(FULL_IMAGE)..."
	docker run --rm -p 8000:8000 --env-file .env $(FULL_IMAGE)

clean: ## Remove local images
	@echo "🧹 Cleaning up..."
	docker rmi $(FULL_IMAGE) 2>/dev/null || true
	@echo "✅ Cleanup complete"