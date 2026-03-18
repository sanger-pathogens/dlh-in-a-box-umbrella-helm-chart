#!/usr/bin/env bash
set -euo pipefail

CHART_PATH="charts/dlh-in-a-box"

render() {
  local values_file="$1"
  echo "--- Rendering with ${values_file}"
  helm template dlh "${CHART_PATH}" -f "${values_file}" >/dev/null
}

if [[ $# -gt 0 ]]; then
  for vf in "$@"; do
    render "$vf"
  done
else
  render examples/values-dev.yaml
  render examples/values-local.yaml
  render examples/values-prod.yaml
  render examples/values-external-s3.yaml
  render examples/values-minio.yaml
fi
