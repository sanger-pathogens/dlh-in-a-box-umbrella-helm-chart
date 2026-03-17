#!/usr/bin/env bash
set -euo pipefail

CHART_PATH="${1:-charts/dlh-in-a-box}"
DEST_DIR="${2:-dist}"

mkdir -p "${DEST_DIR}"
helm package "${CHART_PATH}" --destination "${DEST_DIR}"
