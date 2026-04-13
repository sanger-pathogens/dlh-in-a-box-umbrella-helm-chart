#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

CHART_PATH="${ROOT_DIR}/charts/dlh-in-a-box"

render() {
  local values_file="$1"
  echo "--- Rendering with ${values_file}"
  helm template dlh "${CHART_PATH}" -f "${values_file}" >/dev/null
}

if [[ $# -gt 0 ]]; then
  example_files=("$@")
else
  example_files=(examples/*.yaml)
fi

for vf in "${example_files[@]}"; do
  render "$vf"
done
