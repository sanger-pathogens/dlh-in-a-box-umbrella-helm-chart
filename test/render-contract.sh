#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

CHART_PATH="${ROOT_DIR}/charts/dlh-in-a-box"
FIXTURE_DIR="${ROOT_DIR}/test/render-contract"
LOCAL_VALUES="${ROOT_DIR}/examples/values-local-auth.yaml"
DEV_VALUES="${ROOT_DIR}/examples/values-dev.yaml"
PROD_VALUES="${ROOT_DIR}/examples/values-prod.yaml"

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

echo "--- Positive contract renders"
local_manifest="$(make_tmp_file)"
render_manifest "${local_manifest}" -f "${LOCAL_VALUES}"
dev_manifest="$(make_tmp_file)"
render_manifest "${dev_manifest}" -f "${DEV_VALUES}"
prod_manifest="$(make_tmp_file)"
render_manifest "${prod_manifest}" -f "${PROD_VALUES}"
prefect_automation_manifest="$(make_tmp_file)"
render_manifest "${prefect_automation_manifest}" -f "${DEV_VALUES}" -f "${FIXTURE_DIR}/prefect-automation-enabled.yaml"
prefect_direct_grant_manifest="$(make_tmp_file)"
render_manifest "${prefect_direct_grant_manifest}" -f "${DEV_VALUES}" -f "${FIXTURE_DIR}/prefect-direct-grant-enabled.yaml"
prefect_job_runner_manifest="$(make_tmp_file)"
render_manifest "${prefect_job_runner_manifest}" --namespace dlh-dev -f "${DEV_VALUES}" -f "${FIXTURE_DIR}/prefect-job-runner-enabled.yaml"

# --- Prefect OAuth2 Proxy Defaults & RBAC ---
assert_contains "${dev_manifest}" 'provider = \"keycloak-oidc\"'
assert_contains "${prod_manifest}" 'provider = \"keycloak-oidc\"'
assert_contains "${dev_manifest}" 'allowed_roles = [\"prefect:access\"]'
assert_contains "${prod_manifest}" 'allowed_roles = [\"prefect:access\"]'
assert_contains "${dev_manifest}" 'skip_oidc_discovery = true'
assert_contains "${dev_manifest}" 'redeem_url = \"http://dlh-keycloak.'
assert_contains "${dev_manifest}" '/realms/dlh/protocol/openid-connect/token\"'
assert_contains "${prod_manifest}" 'redeem_url = \"http://dlh-keycloak.'
assert_contains "${prod_manifest}" '/realms/dlh/protocol/openid-connect/token\"'

# --- Prefect Machine Automation & Bearer Tokens ---
assert_contains "${prefect_automation_manifest}" 'skip_jwt_bearer_tokens = true'
assert_contains "${prefect_automation_manifest}" 'api_routes = [ \"^/api/\" ]'
assert_contains "${prefect_automation_manifest}" 'extra_jwt_issuers = \"https://keycloak.dev.example.org/realms/dlh=prefect-api\"'
assert_contains "${prefect_automation_manifest}" 'oidc_extra_audiences = [ \"prefect-api\" ]'
assert_contains "${prefect_automation_manifest}" 'provider_ca_files = [ \"/etc/oauth2-proxy/keycloak-ca/ca.crt\" ]'
assert_contains "${prefect_automation_manifest}" "Prefect Automation"
assert_contains "${prefect_automation_manifest}" "protocolMapper: oidc-audience-mapper"
assert_contains "${prefect_automation_manifest}" "KC_PREFECT_AUTOMATION_CLIENT_SECRET"

# --- Prefect Direct Access Grant (CLI Authentication) ---
assert_contains "${prefect_direct_grant_manifest}" 'skip_jwt_bearer_tokens = true'
assert_contains "${prefect_direct_grant_manifest}" 'api_routes = [ \"^/api/\" ]'
assert_contains "${prefect_direct_grant_manifest}" 'extra_jwt_issuers = \"https://keycloak.dev.example.org/realms/dlh=prefect-api\"'
assert_contains "${prefect_direct_grant_manifest}" 'oidc_extra_audiences = [ \"prefect-api\" ]'
assert_contains "${prefect_direct_grant_manifest}" 'provider_ca_files = [ \"/etc/oauth2-proxy/keycloak-ca/ca.crt\" ]'
assert_contains "${prefect_direct_grant_manifest}" "Prefect Direct Grant"
assert_contains "${prefect_direct_grant_manifest}" "directAccessGrantsEnabled: true"
assert_contains "${prefect_direct_grant_manifest}" "protocolMapper: oidc-audience-mapper"
assert_not_contains "${prefect_direct_grant_manifest}" "KC_PREFECT_AUTOMATION_CLIENT_SECRET"

# --- Prefect Kubernetes Job Runner & Work Pool Template ---
assert_contains "${prefect_job_runner_manifest}" "name: \"prefect-job-runner\""
assert_contains "${prefect_job_runner_manifest}" "app.kubernetes.io/component: prefect-job-runner"
assert_contains "${prefect_job_runner_manifest}" "automountServiceAccountToken: false"
assert_contains "${prefect_job_runner_manifest}" "name: prefect-job-runner-registry"
assert_contains "${prefect_job_runner_manifest}" "type: kubernetes.io/dockerconfigjson"
assert_contains "${prefect_job_runner_manifest}" "ghcr.io"
assert_contains "${prefect_job_runner_manifest}" "name: \"prefect-worker-base-job-template\""
assert_contains "${prefect_job_runner_manifest}" "baseJobTemplate.json"
assert_contains "${prefect_job_runner_manifest}" "\"serviceAccountName\": \"{{ service_account_name }}\""
assert_contains "${prefect_job_runner_manifest}" "\"default\": \"dlh-dev\""
assert_contains "${prefect_job_runner_manifest}" "\"default\": \"prefect-job-runner\""
assert_contains "${prefect_job_runner_manifest}" "sync-base-job-template"
assert_contains "${prefect_job_runner_manifest}" "prefect work-pool update"
