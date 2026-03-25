#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

CHART_PATH="charts/dlh-in-a-box"
FIXTURE_DIR="hack/testdata/render-contract"

tmp_files=()

cleanup() {
  if (( ${#tmp_files[@]} > 0 )); then
    rm -f "${tmp_files[@]}"
  fi
}
trap cleanup EXIT

render_manifest() {
  local output
  output="$(mktemp)"
  tmp_files+=("${output}")
  helm template dlh "${CHART_PATH}" "$@" >"${output}"
  printf '%s\n' "${output}"
}

assert_contains() {
  local file="$1"
  local needle="$2"

  if ! grep -Fq -- "${needle}" "${file}"; then
    echo "Expected rendered manifest to contain: ${needle}" >&2
    echo "Rendered file: ${file}" >&2
    exit 1
  fi
}

assert_not_contains() {
  local file="$1"
  local needle="$2"

  if grep -Fq -- "${needle}" "${file}"; then
    echo "Did not expect rendered manifest to contain: ${needle}" >&2
    echo "Rendered file: ${file}" >&2
    exit 1
  fi
}

expect_fail() {
  local expected="$1"
  shift

  local output
  output="$(mktemp)"
  tmp_files+=("${output}")

  if helm template dlh "${CHART_PATH}" "$@" >"${output}" 2>&1; then
    echo "Expected helm template to fail, but it succeeded: $*" >&2
    exit 1
  fi

  if ! grep -Fq -- "${expected}" "${output}"; then
    echo "Expected helm template failure to include: ${expected}" >&2
    echo "--- Actual output ---" >&2
    cat "${output}" >&2
    echo "---------------------" >&2
    exit 1
  fi
}

echo "--- Positive contract renders"
local_manifest="$(render_manifest -f examples/values-local-auth.yaml)"
dev_manifest="$(render_manifest -f examples/values-dev.yaml)"
prod_manifest="$(render_manifest -f examples/values-prod.yaml)"
shared_manifest="$(render_manifest -f examples/values-shared-auth.yaml)"

assert_not_contains "${local_manifest}" "{{"
assert_not_contains "${dev_manifest}" "{{"
assert_not_contains "${prod_manifest}" "{{"
assert_not_contains "${shared_manifest}" "{{"

assert_contains "${local_manifest}" "name: dlh-openldap"
assert_contains "${local_manifest}" "name: dlh-ranger-admin"
assert_contains "${local_manifest}" "name: dlh-ranger-admin-exception-audit"
assert_contains "${local_manifest}" "name: dlh-platform-home"
assert_contains "${local_manifest}" "Access Admin"
assert_contains "${local_manifest}" "name: dlh-cloudbeaver"
assert_contains "${dev_manifest}" "name: dlh-keycloak-config-cli-env"
assert_contains "${prod_manifest}" "name: dlh-keycloak-config-cli-env"
assert_contains "${prod_manifest}" "name: dlh-ranger-postgresql"
assert_contains "${dev_manifest}" "name: dlh-ranger-admin-exception-audit"
assert_contains "${prod_manifest}" "name: dlh-ranger-admin-exception-audit"
assert_contains "${dev_manifest}" "KC_CLOUDBEAVER_CLIENT_SECRET"
assert_contains "${prod_manifest}" "KC_CLOUDBEAVER_CLIENT_SECRET"
assert_contains "${dev_manifest}" "https://portal.dev.example.org/"
assert_contains "${prod_manifest}" "https://portal.data-platform.example.org/"
assert_contains "${dev_manifest}" "Access Admin"
assert_contains "${prod_manifest}" "Access Admin"
assert_contains "${dev_manifest}" "https://ranger.dev.example.org"
assert_contains "${prod_manifest}" "https://ranger.data-platform.example.org"
assert_contains "${dev_manifest}" "https://cloudbeaver.dev.example.org/oauth2/callback"
assert_contains "${prod_manifest}" "https://cloudbeaver.data-platform.example.org/oauth2/callback"
assert_contains "${shared_manifest}" "https://cloudbeaver.shared.example.org/oauth2/callback"
assert_contains "${dev_manifest}" "https://127.0.0.1:28443/oauth2/callback"
assert_contains "${prod_manifest}" "https://trino.data-platform.example.org/oauth2/callback"
assert_contains "${prod_manifest}" "https://trino.data-platform.example.org"
assert_contains "${prod_manifest}" "https://prefect.data-platform.example.org/oauth2/callback"
assert_contains "${prod_manifest}" "https://prefect.data-platform.example.org"
assert_contains "${dev_manifest}" "http-server.authentication.type=OAUTH2,PASSWORD"
assert_contains "${prod_manifest}" "http-server.authentication.type=OAUTH2,PASSWORD"
assert_contains "${dev_manifest}" "access-control.name=ranger"
assert_contains "${prod_manifest}" "access-control.name=ranger"
assert_contains "${dev_manifest}" 'allowed_groups = [\"dlh-app-prefect\", \"dlh-role-platform-admin\"]'
assert_contains "${prod_manifest}" 'allowed_groups = [\"dlh-app-prefect\", \"dlh-role-platform-admin\"]'
assert_contains "${dev_manifest}" 'allowed_groups = [\"dlh-app-cloudbeaver\", \"dlh-role-platform-admin\"]'
assert_contains "${prod_manifest}" 'allowed_groups = [\"dlh-app-cloudbeaver\", \"dlh-role-platform-admin\"]'
assert_contains "${dev_manifest}" "\"platformRoles\": {"
assert_contains "${dev_manifest}" "\"redcap-readonly-analyst\""
assert_contains "${dev_manifest}" "\"redcap-site-analyst\""
assert_contains "${prod_manifest}" "\"platform-admin\""
assert_contains "${dev_manifest}" "\"roles\": ["
assert_contains "${prod_manifest}" "\"roles\": ["

echo "--- Negative contract renders"
expect_fail \
  "global.environment must be one of the following: \"local\", \"dev\", \"prod\"" \
  -f examples/values-dev.yaml \
  -f "${FIXTURE_DIR}/missing-environment.yaml"

expect_fail \
  "global.dataCatalogs.unclassified.governance is required for dev and prod environments." \
  -f examples/values-dev.yaml \
  -f "${FIXTURE_DIR}/missing-governance.yaml"

expect_fail \
  "global.dataCatalogs.pii_smoke is restricted-identifiable and contains direct or quasi identifiers, so authorization.ranger.bootstrapPolicies must include a masking or row-filter policy for this catalog." \
  -f examples/values-dev.yaml \
  -f "${FIXTURE_DIR}/missing-fine-grained-policy.yaml"

expect_fail \
  "global.identity.external.clients.prefectProxy.allowedGroups must be set in dev and prod so Prefect is not exposed to every authenticated user." \
  -f examples/values-dev.yaml \
  -f "${FIXTURE_DIR}/prefect-missing-groups.yaml"

expect_fail \
  "global.identity.external.clients.cloudbeaverProxy.allowedGroups must be set in dev and prod so CloudBeaver is not exposed to every authenticated user." \
  -f examples/values-dev.yaml \
  -f "${FIXTURE_DIR}/cloudbeaver-missing-groups.yaml"

expect_fail \
  "global.identity.external.clients.platformHome.redirectUris must be set when bundled Keycloak manages the OIDC client." \
  -f examples/values-dev.yaml \
  -f "${FIXTURE_DIR}/platform-home-missing-redirect.yaml"

expect_fail \
  "cloudbeaver-auth-proxy.config.existingSecret must be set when global.identity.external.clients.cloudbeaverProxy.enabled=true." \
  -f examples/values-dev.yaml \
  -f "${FIXTURE_DIR}/cloudbeaver-missing-secret.yaml"

expect_fail \
  "global.identity.external.clients.trino.redirectUris must not use wildcard values outside local environments." \
  -f examples/values-prod.yaml \
  -f "${FIXTURE_DIR}/wildcard-redirect.yaml"

expect_fail \
  "global.identity.provider.keycloak.configCliEnvExistingSecret is required when bundled Keycloak is enabled." \
  -f examples/values-dev.yaml \
  -f "${FIXTURE_DIR}/missing-config-cli-secret.yaml"

expect_fail \
  "global.environment must be one of the following: \"local\", \"dev\", \"prod\"" \
  -f examples/values-shared-auth.yaml \
  -f "${FIXTURE_DIR}/missing-identity-environment.yaml"

expect_fail \
  "The top-level identity block is no longer supported. Move all shared identity settings under global.identity." \
  -f examples/values-dev.yaml \
  -f "${FIXTURE_DIR}/legacy-top-level-identity.yaml"

expect_fail \
  "Use global.identity.external.clients.trino.passwordAuthEnabled instead of trino.server.config.authenticationType=PASSWORD when shared identity is enabled." \
  -f examples/values-dev.yaml \
  -f "${FIXTURE_DIR}/legacy-trino-authentication-type.yaml"

expect_fail \
  "global.authorization.platformRoles.platform-admin.apps: Additional property notARealApp is not allowed" \
  -f examples/values-dev.yaml \
  -f "${FIXTURE_DIR}/invalid-platform-role-app.yaml"

expect_fail \
  "global.authorization.platformRoleExceptions[0].approvalRef must be set." \
  -f examples/values-dev.yaml \
  -f "${FIXTURE_DIR}/exception-missing-metadata.yaml"
