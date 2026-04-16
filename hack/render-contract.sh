#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

CHART_PATH="${ROOT_DIR}/charts/dlh-in-a-box"
FIXTURE_DIR="${ROOT_DIR}/hack/testdata/render-contract"
LOCAL_VALUES="${ROOT_DIR}/examples/values-local-auth.yaml"
DEV_VALUES="${ROOT_DIR}/examples/values-dev.yaml"
PROD_VALUES="${ROOT_DIR}/examples/values-prod.yaml"
SHARED_VALUES="${ROOT_DIR}/examples/values-shared-auth.yaml"

tmp_files=()

cleanup() {
  if (( ${#tmp_files[@]} > 0 )); then
    rm -f "${tmp_files[@]}"
  fi
}
trap cleanup EXIT

make_tmp_file() {
  local output
  output="$(mktemp)"
  tmp_files+=("${output}")
  printf '%s\n' "${output}"
}

render_manifest() {
  local output="$1"
  shift
  local manifest
  manifest="$(helm template dlh "${CHART_PATH}" "$@")"
  printf '%s' "${manifest}" >"${output}"
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
default_manifest="$(make_tmp_file)"
render_manifest "${default_manifest}"
local_manifest="$(make_tmp_file)"
render_manifest "${local_manifest}" -f "${LOCAL_VALUES}"
dev_manifest="$(make_tmp_file)"
render_manifest "${dev_manifest}" -f "${DEV_VALUES}"
prod_manifest="$(make_tmp_file)"
render_manifest "${prod_manifest}" -f "${PROD_VALUES}"
shared_manifest="$(make_tmp_file)"
render_manifest "${shared_manifest}" -f "${SHARED_VALUES}"
prefect_automation_manifest="$(make_tmp_file)"
render_manifest "${prefect_automation_manifest}" -f "${DEV_VALUES}" -f "${FIXTURE_DIR}/prefect-automation-enabled.yaml"
prefect_direct_grant_manifest="$(make_tmp_file)"
render_manifest "${prefect_direct_grant_manifest}" -f "${DEV_VALUES}" -f "${FIXTURE_DIR}/prefect-direct-grant-enabled.yaml"

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
assert_contains "${local_manifest}" 'add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;'
assert_contains "${local_manifest}" 'add_header X-Content-Type-Options "nosniff" always;'
assert_contains "${local_manifest}" 'add_header Referrer-Policy "strict-origin-when-cross-origin" always;'
assert_contains "${local_manifest}" "name: dlh-cloudbeaver"
assert_contains "${local_manifest}" "/access-control"
assert_not_contains "${local_manifest}" "ldap-directory"
assert_not_contains "${local_manifest}" "access-control.name=ranger"
assert_contains "${local_manifest}" "access-control.name=file"
assert_contains "${local_manifest}" "registrationAllowed: true"
assert_contains "${local_manifest}" "verifyEmail: false"
assert_contains "${local_manifest}" "\"accessControlEnabled\": false"
assert_contains "${local_manifest}" "platform-app-cloudbeaver"
assert_contains "${local_manifest}" "platform-app-prefect"
assert_contains "${local_manifest}" "trino-cli"
assert_contains "${local_manifest}" "http-server.authentication.type=OAUTH2"
assert_not_contains "${local_manifest}" "http-server.authentication.type=OAUTH2,PASSWORD"
assert_not_contains "${local_manifest}" "name: dlh-ranger-admin-usersync"
assert_contains "${local_manifest}" "name: dlh-ranger-admin-local-user-sync"
assert_contains "${dev_manifest}" "name: dlh-keycloak-config-cli-env"
assert_contains "${prod_manifest}" "name: dlh-keycloak-config-cli-env"
assert_contains "${prod_manifest}" "name: dlh-ranger-postgresql"
assert_contains "${dev_manifest}" "name: dlh-ranger-admin-exception-audit"
assert_contains "${prod_manifest}" "name: dlh-ranger-admin-exception-audit"
assert_contains "${dev_manifest}" "KC_CLOUDBEAVER_CLIENT_SECRET"
assert_contains "${prod_manifest}" "KC_CLOUDBEAVER_CLIENT_SECRET"
assert_contains "${dev_manifest}" "https://portal.dev.example.org/"
assert_contains "${prod_manifest}" "https://portal.data-platform.example.org/"
assert_contains "${dev_manifest}" "https://jupyterhub.dev.example.org/hub/oauth_callback"
assert_contains "${prod_manifest}" "https://jupyterhub.data-platform.example.org/hub/oauth_callback"
assert_contains "${dev_manifest}" "Administration"
assert_contains "${prod_manifest}" "Administration"
assert_contains "${dev_manifest}" 'add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;'
assert_contains "${prod_manifest}" 'add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;'
assert_contains "${dev_manifest}" 'add_header X-Content-Type-Options "nosniff" always;'
assert_contains "${prod_manifest}" 'add_header X-Content-Type-Options "nosniff" always;'
assert_contains "${dev_manifest}" 'add_header Referrer-Policy "strict-origin-when-cross-origin" always;'
assert_contains "${prod_manifest}" 'add_header Referrer-Policy "strict-origin-when-cross-origin" always;'
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
assert_contains "${dev_manifest}" "trino-cli"
assert_contains "${prod_manifest}" "trino-cli"
assert_contains "${dev_manifest}" "platform-app-jupyterhub"
assert_contains "${prod_manifest}" "platform-app-jupyterhub"
assert_contains "${dev_manifest}" "KC_JUPYTERHUB_CLIENT_SECRET"
assert_contains "${prod_manifest}" "KC_JUPYTERHUB_CLIENT_SECRET"
assert_contains "${dev_manifest}" "ICDDRB_Trino_Demo.ipynb"
assert_contains "${prod_manifest}" "ICDDRB_Trino_Demo.ipynb"
assert_contains "${dev_manifest}" "Python 3 (Trino Demo)"
assert_contains "${prod_manifest}" "Python 3 (Trino Demo)"
assert_contains "${dev_manifest}" "jupyterhub.dev.example.org"
assert_contains "${prod_manifest}" "jupyterhub.data-platform.example.org"
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
assert_contains "${dev_manifest}" 'http-server.authentication.oauth2.token-url='
assert_contains "${prod_manifest}" 'http-server.authentication.oauth2.token-url='
assert_contains "${dev_manifest}" 'protocol/openid-connect/token'
assert_contains "${prod_manifest}" 'protocol/openid-connect/token'
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
assert_contains "${dev_manifest}" "\"user\":\"cloudbeaver-service\",\"catalog\":\"system\",\"allow\":\"all\""
assert_contains "${dev_manifest}" "\"user\":\"superset-service\",\"catalog\":\"system\",\"allow\":\"all\""

echo "--- Negative contract renders"
expect_fail_any \
  "global.environment must be one of the following: \"local\", \"dev\", \"prod\"" \
  "value must be one of 'local', 'dev', 'prod'" \
  -- \
  -f "${DEV_VALUES}" \
  -f "${FIXTURE_DIR}/missing-environment.yaml"

expect_fail \
  "global.dataCatalogs.unclassified.governance is required for dev and prod environments." \
  -f "${DEV_VALUES}" \
  -f "${FIXTURE_DIR}/missing-governance.yaml"

expect_fail \
  "global.dataCatalogs.pii_smoke is restricted-identifiable and contains direct or quasi identifiers, so authorization.ranger.bootstrapPolicies must include a masking or row-filter policy for this catalog." \
  -f "${DEV_VALUES}" \
  -f "${FIXTURE_DIR}/missing-fine-grained-policy.yaml"

expect_fail \
  "global.identity.external.clients.prefectProxy.allowedGroups must be set in dev and prod so Prefect is not exposed to every authenticated user." \
  -f "${DEV_VALUES}" \
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
  -f "${DEV_VALUES}" \
  -f "${FIXTURE_DIR}/cloudbeaver-missing-groups.yaml"

expect_fail \
  "global.identity.external.clients.platformHome.redirectUris must be set when bundled Keycloak manages the OIDC client." \
  -f "${DEV_VALUES}" \
  -f "${FIXTURE_DIR}/platform-home-missing-redirect.yaml"

expect_fail \
  "cloudbeaver-auth-proxy.config.existingSecret must be set when global.identity.external.clients.cloudbeaverProxy.enabled=true." \
  -f "${DEV_VALUES}" \
  -f "${FIXTURE_DIR}/cloudbeaver-missing-secret.yaml"

expect_fail \
  "global.identity.external.clients.trino.redirectUris must not use wildcard values outside local environments." \
  -f "${PROD_VALUES}" \
  -f "${FIXTURE_DIR}/wildcard-redirect.yaml"

expect_fail \
  "global.identity.provider.keycloak.configCliEnvExistingSecret is required when bundled Keycloak is enabled." \
  -f "${DEV_VALUES}" \
  -f "${FIXTURE_DIR}/missing-config-cli-secret.yaml"

expect_fail \
  "global.identity.directory.ldap.url is required when Trino identity integration is enabled." \
  -f "${DEV_VALUES}" \
  -f "${FIXTURE_DIR}/missing-directory-url.yaml"

expect_fail \
  "global.identity.directory.ldap.enabled must be true when Trino LDAP PASSWORD auth is enabled through the shared identity contract." \
  -f "${LOCAL_VALUES}" \
  -f "${FIXTURE_DIR}/bootstrap-users-base.yaml" \
  -f "${FIXTURE_DIR}/bootstrap-password-auth-without-ldap.yaml"

expect_fail \
  "global.authorization.ranger.usersync.enabled must be false when using bundled Keycloak bootstrapUsers without an organizational LDAP connection." \
  -f "${LOCAL_VALUES}" \
  -f "${FIXTURE_DIR}/bootstrap-users-base.yaml" \
  -f "${FIXTURE_DIR}/bootstrap-usersync-without-ldap.yaml"

expect_fail \
  "global.identity.provider.keycloak.registration.enabled must be true when global.identity.directory.mode=keycloakLocal." \
  -f "${LOCAL_VALUES}" \
  -f "${FIXTURE_DIR}/keycloak-local-registration-disabled.yaml"

expect_fail \
  "global.identity.external.clients.trino.passwordAuthMode must be file when global.identity.directory.mode=keycloakLocal. LDAP PASSWORD auth is not allowed in that mode." \
  -f "${LOCAL_VALUES}" \
  -f "${FIXTURE_DIR}/keycloak-local-trino-password-auth-enabled.yaml"

expect_fail \
  "global.authorization.ranger.usersync.enabled must be false when global.identity.directory.mode=keycloakLocal." \
  -f "${LOCAL_VALUES}" \
  -f "${FIXTURE_DIR}/keycloak-local-usersync-enabled.yaml"

expect_fail \
  "global.identity.directory.ldap.enabled must be false when global.identity.directory.mode=keycloakLocal." \
  -f "${LOCAL_VALUES}" \
  -f "${FIXTURE_DIR}/keycloak-local-ldap-enabled.yaml"

expect_fail_any \
  "global.environment must be one of the following: \"local\", \"dev\", \"prod\"" \
  "value must be one of 'local', 'dev', 'prod'" \
  -- \
  -f "${SHARED_VALUES}" \
  -f "${FIXTURE_DIR}/missing-identity-environment.yaml"

expect_fail \
  "The top-level identity block is no longer supported. Move all shared identity settings under global.identity." \
  -f "${DEV_VALUES}" \
  -f "${FIXTURE_DIR}/legacy-top-level-identity.yaml"

expect_fail \
  "Use global.identity.external.clients.trino.passwordAuthEnabled instead of trino.server.config.authenticationType=PASSWORD when shared identity is enabled." \
  -f "${DEV_VALUES}" \
  -f "${FIXTURE_DIR}/legacy-trino-authentication-type.yaml"

expect_fail_any \
  "global.authorization.platformRoles.platform-admin.apps: Additional property notARealApp is not allowed" \
  "additional properties 'notARealApp' not allowed" \
  -- \
  -f "${DEV_VALUES}" \
  -f "${FIXTURE_DIR}/invalid-platform-role-app.yaml"

expect_fail \
  "global.authorization.platformRoleExceptions[0].approvalRef must be set." \
  -f "${DEV_VALUES}" \
  -f "${FIXTURE_DIR}/exception-missing-metadata.yaml"
