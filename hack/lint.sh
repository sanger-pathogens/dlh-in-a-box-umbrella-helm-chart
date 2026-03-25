#!/usr/bin/env bash
set -euo pipefail

CHART_PATH="charts/dlh-in-a-box"
EXAMPLE_FILES=(examples/*.yaml)

./hack/license-check.sh
./hack/docs-check.sh
./hack/security-check.sh
./hack/render-contract.sh

bash -n hack/*.sh
ruby -e 'require "json"; JSON.parse(File.read("charts/dlh-in-a-box/values.schema.json"))'

helm lint "${CHART_PATH}"

for values_file in "${EXAMPLE_FILES[@]}"; do
  echo "--- Linting with ${values_file}"
  helm lint "${CHART_PATH}" -f "${values_file}"
done
