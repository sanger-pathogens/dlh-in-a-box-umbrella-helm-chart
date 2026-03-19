CHART_PATH ?= charts/dlh-in-a-box
DEST_DIR ?= dist
LOCAL_VALUES ?= examples/values-local.yaml
RELEASE_NAME ?= dlh
NAMESPACE ?= data-lakehouse-local

.DEFAULT_GOAL := help

.PHONY: help deps docs-check lint template package smoke-install local-install

help: ## Show common maintainer targets.
	@awk 'BEGIN {FS = ": ## "}; /^[a-zA-Z0-9_.-]+: ## / {printf "%-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

deps: ## Refresh Helm dependencies and Chart.lock.
	./hack/helm-dependency-update.sh

docs-check: ## Verify maintained directories still have local guide files.
	./hack/docs-check.sh

lint: ## Run repository validation, including license, docs, schema, and Helm lint checks.
	./hack/lint.sh

template: ## Render the chart against all example overlays.
	./hack/template.sh

package: ## Package the chart into dist/.
	./hack/package.sh $(CHART_PATH) $(DEST_DIR)

smoke-install: ## Install the validated local overlay and wait for workloads to become ready.
	./hack/smoke-install.sh $(CHART_PATH) $(LOCAL_VALUES)

local-install: ## Install the validated local overlay into the target namespace.
	helm upgrade --install $(RELEASE_NAME) $(CHART_PATH) \
		-n $(NAMESPACE) \
		--create-namespace \
		-f $(LOCAL_VALUES)
