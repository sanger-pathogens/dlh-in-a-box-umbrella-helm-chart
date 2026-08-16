#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

bash -n "${ROOT_DIR}"/hack/*.sh
"${ROOT_DIR}"/hack/license-check.sh
"${ROOT_DIR}"/hack/docs-check.sh
"${ROOT_DIR}"/hack/security-check.sh
"${ROOT_DIR}"/test/render-contract.sh
"${ROOT_DIR}"/hack/helm-lint.sh

