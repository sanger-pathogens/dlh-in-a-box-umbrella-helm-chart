#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

bash -n "${ROOT_DIR}"/hack/*.sh
"${ROOT_DIR}"/scripts/license-check.sh
"${ROOT_DIR}"/scripts/docs-check.sh
"${ROOT_DIR}"/scripts/security-check.sh
"${ROOT_DIR}"/test/render-contract.sh
"${ROOT_DIR}"/scripts/helm-lint.sh

