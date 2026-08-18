#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

CHART_PATH="${ROOT_DIR}/charts/dlh-in-a-box"
EXAMPLE_FILES=(examples/*.yaml)

ruby -e 'require "json"; JSON.parse(File.read("charts/dlh-in-a-box/values.schema.json"))'

helm lint "${CHART_PATH}"

for values_file in "${EXAMPLE_FILES[@]}"; do
  echo "--- Linting with ${values_file}"
  helm lint "${CHART_PATH}" -f "${values_file}"
done
