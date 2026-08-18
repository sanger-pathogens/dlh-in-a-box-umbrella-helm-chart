CHART_PATH ?= charts/dlh-in-a-box
DEST_DIR ?= dist
LOCAL_VALUES ?= examples/values-local-auth.yaml
RELEASE_NAME ?= dlh
NAMESPACE ?= data-lakehouse-local

.DEFAULT_GOAL := help

.PHONY: help deps docs-check render-contract template package smoke-install local-install \
	script-check license-check security-check helm-lint precommit

help: ## Show common maintainer targets.
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z0-9_.-]+:.*## / {printf "%-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

deps: ## Refresh Helm dependencies and Chart.lock.
	./scripts/helm/helm-dependency-update.sh

docs-check: ## Verify maintained directories still have local guide files.
	./scripts/repo/docs-check.sh

render-contract: ## Prove supported renders succeed and unsafe values fail.
	./test/render-contract.sh

template: ## Render the chart against all example overlays.
	./scripts/helm/template.sh

package: ## Package the chart into dist/.
	./scripts/helm/package.sh $(CHART_PATH) $(DEST_DIR)

smoke-install: ## Install the validated local overlay and wait for workloads to become ready.
	./scripts/helm/smoke-install.sh $(CHART_PATH) $(LOCAL_VALUES)

local-install: ## Install the validated local overlay into the target namespace.
	helm upgrade --install $(RELEASE_NAME) $(CHART_PATH) \
		-n $(NAMESPACE) \
		--create-namespace \
		-f $(LOCAL_VALUES)

script-check: ## Syntax check all shell scripts under scripts/.
	find "scripts" -name '*.sh' -exec bash -n {} +

license-check: ## Verify license headers are present.
	./scripts/repo/license-check.sh

security-check: ## Scan for common security issues (secrets, unsafe patterns).
	./scripts/repo/security-check.sh

helm-lint: ## Run `helm lint` against the chart and all example overlays.
	./scripts/helm/helm-lint.sh

verify: script-check deps license-check security-check docs-check render-contract helm-lint template package ## Run every check the pre-commit hooks run, in the same order.