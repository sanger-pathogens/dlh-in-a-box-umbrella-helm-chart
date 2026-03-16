#!/usr/bin/env bash
set -euo pipefail

CHART_PATH="charts/dlh-in-a-box"

helm lint "${CHART_PATH}"
helm lint "${CHART_PATH}" -f examples/values-dev.yaml
helm lint "${CHART_PATH}" -f examples/values-prod.yaml
helm lint "${CHART_PATH}" -f examples/values-external-s3.yaml
helm lint "${CHART_PATH}" -f examples/values-minio.yaml
