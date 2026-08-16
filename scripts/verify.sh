#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

find "${ROOT_DIR}/scripts" -name '*.sh' -exec bash -n {} +
"${ROOT_DIR}"/scripts/repo/license-check.sh
"${ROOT_DIR}"/scripts/repo/docs-check.sh
"${ROOT_DIR}"/scripts/repo/security-check.sh
"${ROOT_DIR}"/test/render-contract.sh
"${ROOT_DIR}"/scripts/helm/helm-lint.sh

