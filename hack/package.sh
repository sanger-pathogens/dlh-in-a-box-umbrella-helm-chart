#!/usr/bin/env bash
set -euo pipefail

CHART_PATH="${1:-charts/dlh-in-a-box}"
DEST_DIR="${2:-dist}"
CHART_VERSION="${3:-}"
APP_VERSION="${4:-}"

mkdir -p "${DEST_DIR}"

args=(
  "${CHART_PATH}"
  --destination "${DEST_DIR}"
)

if [[ -n "${CHART_VERSION}" ]]; then
  args+=(--version "${CHART_VERSION}")
fi

if [[ -n "${APP_VERSION}" ]]; then
  args+=(--app-version "${APP_VERSION}")
fi

helm package "${args[@]}"
