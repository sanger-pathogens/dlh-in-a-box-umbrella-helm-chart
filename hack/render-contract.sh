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

expect_fail_any() {
  local output
  output="$(mktemp)"
  tmp_files+=("${output}")

  local expected_matches=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --)
        shift
        break
        ;;
      *)
        expected_matches+=("$1")
        shift
        ;;
    esac
  done

  if helm template dlh "${CHART_PATH}" "$@" >"${output}" 2>&1; then
    echo "Expected helm template to fail, but it succeeded: $*" >&2
    exit 1
  fi

  local expected=""
  for expected in "${expected_matches[@]}"; do
    if grep -Fq -- "${expected}" "${output}"; then
      return 0
    fi
  done

  echo "Expected helm template failure to include one of:" >&2
  printf '  - %s\n' "${expected_matches[@]}" >&2
  echo "--- Actual output ---" >&2
  cat "${output}" >&2
  echo "---------------------" >&2
  exit 1
}

echo "--- Positive contract renders"
default_manifest="$(render_manifest)"
local_manifest="$(render_manifest -f examples/values-local-auth.yaml)"
dev_manifest="$(render_manifest -f examples/values-dev.yaml)"
prod_manifest="$(render_manifest -f examples/values-prod.yaml)"
shared_manifest="$(render_manifest -f examples/values-shared-auth.yaml)"
prefect_automation_manifest="$(render_manifest -f examples/values-dev.yaml -f "${FIXTURE_DIR}/prefect-automation-enabled.yaml")"
prefect_direct_grant_manifest="$(render_manifest -f examples/values-dev.yaml -f "${FIXTURE_DIR}/prefect-direct-grant-enabled.yaml")"

assert_not_contains "${default_manifest}" "{{"
assert_not_contains "${local_manifest}" "{{"
assert_not_contains "${dev_manifest}" "{{"
assert_not_contains "${prod_manifest}" "{{"
assert_not_contains "${shared_manifest}" "{{"

assert_not_contains "${default_manifest}" "icddr,b"
assert_not_contains "${default_manifest}" "icddrb.org"
assert_not_contains "${default_manifest}" "background_logo"
assert_not_contains "${default_manifest}" "FSLolaWeb"
assert_not_contains "${default_manifest}" "SourceSansPro"
assert_contains "${local_manifest}" "name: dlh-ranger-admin"
assert_contains "${local_manifest}" "name: dlh-ranger-admin-exception-audit"
assert_contains "${local_manifest}" "name: dlh-platform-home"
assert_contains "${local_manifest}" "Administration"
assert_contains "${local_manifest}" "name: dlh-cloudbeaver"
assert_contains "${local_manifest}" 'username: "admin"'
assert_contains "${local_manifest}" "KC_BOOTSTRAP_ADMIN_PASSWORD"
assert_contains "${local_manifest}" "/access-control"
assert_not_contains "${local_manifest}" "ldap-directory"
assert_not_contains "${local_manifest}" "access-control.name=ranger"
assert_contains "${local_manifest}" "access-control.name=file"
assert_contains "${dev_manifest}" "name: dlh-keycloak-config-cli-env"
assert_contains "${prod_manifest}" "name: dlh-keycloak-config-cli-env"
assert_contains "${prod_manifest}" "name: dlh-ranger-postgresql"
assert_contains "${dev_manifest}" "name: dlh-ranger-admin-exception-audit"
assert_contains "${prod_manifest}" "name: dlh-ranger-admin-exception-audit"
assert_contains "${dev_manifest}" "KC_CLOUDBEAVER_CLIENT_SECRET"
assert_contains "${prod_manifest}" "KC_CLOUDBEAVER_CLIENT_SECRET"
assert_contains "${dev_manifest}" "https://portal.dev.example.org/"
assert_contains "${prod_manifest}" "https://portal.data-platform.example.org/"
assert_contains "${dev_manifest}" "Administration"
assert_contains "${prod_manifest}" "Administration"
assert_not_contains "${dev_manifest}" "Unified access to approved platform tools"
assert_not_contains "${prod_manifest}" "Unified access to approved platform tools"
assert_not_contains "${dev_manifest}" "How access works"
assert_not_contains "${prod_manifest}" "How access works"
assert_not_contains "${dev_manifest}" "Query sessions still use your Trino credentials."
assert_not_contains "${prod_manifest}" "Query sessions still use your Trino credentials."
assert_contains "${dev_manifest}" "https://ranger.dev.example.org"
assert_contains "${prod_manifest}" "https://ranger.data-platform.example.org"
assert_contains "${dev_manifest}" "https://cloudbeaver.dev.example.org/oauth2/callback"
assert_contains "${prod_manifest}" "https://cloudbeaver.data-platform.example.org/oauth2/callback"
assert_contains "${shared_manifest}" "https://cloudbeaver.shared.example.org/oauth2/callback"
assert_contains "${dev_manifest}" "https://trino.dev.example.org/oauth2/callback"
assert_contains "${prod_manifest}" "https://trino.data-platform.example.org/oauth2/callback"
assert_contains "${prod_manifest}" "https://trino.data-platform.example.org"
assert_contains "${prod_manifest}" "https://prefect.data-platform.example.org/oauth2/callback"
assert_contains "${prod_manifest}" "https://prefect.data-platform.example.org"
assert_contains "${dev_manifest}" "http-server.authentication.type=OAUTH2,PASSWORD"
assert_contains "${prod_manifest}" "http-server.authentication.type=OAUTH2,PASSWORD"
assert_not_contains "${dev_manifest}" "access-control.name=ranger"
assert_not_contains "${prod_manifest}" "access-control.name=ranger"
assert_contains "${dev_manifest}" "access-control.name=file"
assert_contains "${prod_manifest}" "access-control.name=file"
assert_contains "${dev_manifest}" 'allowed_groups = [\"platform-app-prefect\", \"platform-role-platform-admin\"]'
assert_contains "${prod_manifest}" 'allowed_groups = [\"platform-app-prefect\", \"platform-role-platform-admin\"]'
assert_contains "${dev_manifest}" 'allowed_groups = [\"platform-app-cloudbeaver\", \"platform-role-platform-admin\"]'
assert_contains "${prod_manifest}" 'allowed_groups = [\"platform-app-cloudbeaver\", \"platform-role-platform-admin\"]'
assert_contains "${dev_manifest}" 'skip_oidc_discovery = true'
assert_contains "${dev_manifest}" 'redeem_url = \"http://dlh-keycloak.'
assert_contains "${dev_manifest}" '/realms/dlh/protocol/openid-connect/token\"'
assert_contains "${prod_manifest}" 'redeem_url = \"http://dlh-keycloak.'
assert_contains "${prod_manifest}" '/realms/dlh/protocol/openid-connect/token\"'
assert_contains "${prefect_automation_manifest}" 'skip_jwt_bearer_tokens = true'
assert_contains "${prefect_automation_manifest}" 'api_routes = [ \"^/api/\" ]'
assert_contains "${prefect_automation_manifest}" 'extra_jwt_issuers = \"https://keycloak.dev.example.org/realms/dlh=prefect-api\"'
assert_contains "${prefect_automation_manifest}" "Prefect Automation"
assert_contains "${prefect_automation_manifest}" "protocolMapper: oidc-audience-mapper"
assert_contains "${prefect_automation_manifest}" "KC_PREFECT_AUTOMATION_CLIENT_SECRET"
assert_contains "${prefect_direct_grant_manifest}" 'skip_jwt_bearer_tokens = true'
assert_contains "${prefect_direct_grant_manifest}" 'api_routes = [ \"^/api/\" ]'
assert_contains "${prefect_direct_grant_manifest}" 'extra_jwt_issuers = \"https://keycloak.dev.example.org/realms/dlh=prefect-api\"'
assert_contains "${prefect_direct_grant_manifest}" "Prefect Direct Grant"
assert_contains "${prefect_direct_grant_manifest}" "directAccessGrantsEnabled: true"
assert_contains "${prefect_direct_grant_manifest}" "protocolMapper: oidc-audience-mapper"
assert_not_contains "${prefect_direct_grant_manifest}" "KC_PREFECT_AUTOMATION_CLIENT_SECRET"
assert_contains "${dev_manifest}" "\"platformRoles\": {"
assert_contains "${dev_manifest}" "\"data-analyst\""
assert_contains "${dev_manifest}" "\"principal-investigator\""
assert_contains "${prod_manifest}" "\"platform-admin\""
assert_contains "${dev_manifest}" "\"roles\": ["
assert_contains "${prod_manifest}" "\"roles\": ["

echo "--- Negative contract renders"
expect_fail_any \
  "global.environment must be one of the following: \"local\", \"dev\", \"prod\"" \
  "value must be one of 'local', 'dev', 'prod'" \
  -- \
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
  "global.identity.external.clients.prefectAutomation.clientId is required when machine access for Prefect is enabled." \
  -f examples/values-dev.yaml \
  -f "${FIXTURE_DIR}/prefect-automation-missing-client-id.yaml"

expect_fail \
  "global.identity.external.clients.prefectAutomation.enabled requires prefect.authProxy.enabled=true." \
  -f examples/values-dev.yaml \
  -f "${FIXTURE_DIR}/prefect-automation-authproxy-disabled.yaml"

expect_fail \
  "global.identity.external.clients.prefectAutomation.enabled requires global.identity.external.clients.prefectProxy.enabled=true." \
  -f examples/values-dev.yaml \
  -f "${FIXTURE_DIR}/prefect-automation-prefectproxy-disabled.yaml"

expect_fail \
  "global.identity.external.clients.prefectDirectGrant.clientId is required when developer access for Prefect is enabled." \
  -f examples/values-dev.yaml \
  -f "${FIXTURE_DIR}/prefect-direct-grant-missing-client-id.yaml"

expect_fail \
  "global.identity.external.clients.prefectDirectGrant.enabled requires prefect.authProxy.enabled=true." \
  -f examples/values-dev.yaml \
  -f "${FIXTURE_DIR}/prefect-direct-grant-authproxy-disabled.yaml"

expect_fail \
  "global.identity.external.clients.prefectDirectGrant.enabled requires global.identity.external.clients.prefectProxy.enabled=true." \
  -f examples/values-dev.yaml \
  -f "${FIXTURE_DIR}/prefect-direct-grant-prefectproxy-disabled.yaml"

expect_fail \
  "global.identity.external.clients.prefectAutomation.tokenAudience must match global.identity.external.clients.prefectDirectGrant.tokenAudience when both Prefect bearer-token clients are enabled." \
  -f examples/values-dev.yaml \
  -f "${FIXTURE_DIR}/prefect-token-audience-mismatch.yaml"

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
  "global.identity.directory.ldap.url is required when Trino identity integration is enabled." \
  -f examples/values-dev.yaml \
  -f "${FIXTURE_DIR}/missing-directory-url.yaml"

expect_fail \
  "global.identity.directory.ldap.enabled must be true when Trino LDAP PASSWORD auth is enabled through the shared identity contract." \
  -f examples/values-local-auth.yaml \
  -f "${FIXTURE_DIR}/bootstrap-password-auth-without-ldap.yaml"

expect_fail \
  "global.authorization.ranger.usersync.enabled must be false when using bundled Keycloak bootstrapUsers without an organizational LDAP connection." \
  -f examples/values-local-auth.yaml \
  -f "${FIXTURE_DIR}/bootstrap-usersync-without-ldap.yaml"

expect_fail_any \
  "global.environment must be one of the following: \"local\", \"dev\", \"prod\"" \
  "value must be one of 'local', 'dev', 'prod'" \
  -- \
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
