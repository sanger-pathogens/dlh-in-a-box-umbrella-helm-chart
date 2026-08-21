#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

CHART_PATH="${1:-charts/dlh-in-a-box}"
VALUES_FILE="${2:-examples/values-local-auth.yaml}"
RELEASE_NAME="${RELEASE_NAME:-dlh}"
NAMESPACE="${NAMESPACE:-data-lakehouse-local}"
TIMEOUT="${TIMEOUT:-30m}"
ARTIFACT_DIR="${ARTIFACT_DIR:-}"
SKIP_DEPENDENCY_UPDATE="${SKIP_DEPENDENCY_UPDATE:-false}"
RESET_RELEASE_STATE="${RESET_RELEASE_STATE:-true}"

transient_kube_error() {
  local message="${1:-}"
  [[ "${message}" == *"the server was unable to return a response in the time allotted"* ]] \
    || [[ "${message}" == *"Kubernetes cluster unreachable"* ]] \
    || [[ "${message}" == *"EOF"* ]] \
    || [[ "${message}" == *"Client.Timeout exceeded while awaiting headers"* ]]
}

run_with_retries() {
  local attempts="$1"
  local sleep_seconds="$2"
  shift 2

  local attempt=1
  local output=""

  while true; do
    set +e
    output="$("$@" 2>&1)"
    local exit_code=$?
    set -e

    if [[ ${exit_code} -eq 0 ]]; then
      [[ -n "${output}" ]] && printf '%s\n' "${output}"
      return 0
    fi

    if (( attempt >= attempts )) || ! transient_kube_error "${output}"; then
      [[ -n "${output}" ]] && printf '%s\n' "${output}" >&2
      return "${exit_code}"
    fi

    printf 'Transient Kubernetes error on attempt %d/%d; retrying in %ss...\n' \
      "${attempt}" "${attempts}" "${sleep_seconds}" >&2
    [[ -n "${output}" ]] && printf '%s\n' "${output}" >&2
    sleep "${sleep_seconds}"
    attempt=$((attempt + 1))
  done
}

seed_secret() {
  local name="$1"
  shift

  kubectl create secret generic "${name}" \
    -n "${NAMESPACE}" \
    "$@" \
    --dry-run=client \
    -o yaml | kubectl apply -f -
}

wait_for_namespace_deletion() {
  local attempts=60

  while kubectl get namespace "${NAMESPACE}" >/dev/null 2>&1; do
    if (( attempts == 0 )); then
      echo "Timed out waiting for namespace ${NAMESPACE} to be deleted." >&2
      return 1
    fi

    sleep 5
    attempts=$((attempts - 1))
  done
}

reset_release_state() {
  if helm status "${RELEASE_NAME}" -n "${NAMESPACE}" >/dev/null 2>&1; then
    helm uninstall "${RELEASE_NAME}" -n "${NAMESPACE}" --wait --timeout 10m || true
  fi

  if kubectl get namespace "${NAMESPACE}" >/dev/null 2>&1; then
    kubectl delete namespace "${NAMESPACE}" --wait=true --timeout=10m || true
    wait_for_namespace_deletion
  fi
}

seed_local_auth_demo_secrets() {
  kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

  seed_secret dlh-keycloak-admin \
    --from-literal=adminPassword=admin123

  seed_secret dlh-keycloak-postgresql \
    --from-literal=password=keycloakdb123 \
    --from-literal=postgres-password=keycloakdbadmin123

  seed_secret dlh-directory-bind \
    --from-literal=bindPassword=local-directory-bind-password

  seed_secret dlh-oidc-clients \
    --from-literal=trinoClientSecret=local-trino-client-secret \
    --from-literal=supersetClientSecret=local-superset-client-secret \
    --from-literal=datahubClientSecret=local-datahub-client-secret \
    --from-literal=jupyterhubClientSecret=local-jupyterhub-client-secret \
    --from-literal=cloudbeaverClientSecret=local-cloudbeaver-client-secret \
    --from-literal=prefectClientSecret=local-prefect-client-secret

  seed_secret dlh-trino-internal-communication \
    --from-literal=sharedSecret=local-trino-shared-secret

  seed_secret dlh-cloudbeaver-oauth2-proxy \
    --from-literal=client-id=cloudbeaver \
    --from-literal=client-secret=local-cloudbeaver-client-secret \
    --from-literal=cookie-secret=abcdef0123456789abcdef0123456789

  seed_secret dlh-prefect-oauth2-proxy \
    --from-literal=client-id=prefect \
    --from-literal=client-secret=local-prefect-client-secret \
    --from-literal=cookie-secret=0123456789abcdef0123456789abcdef

  seed_secret dlh-cloudbeaver-bootstrap \
    --from-literal=admin-name=cbadmin \
    --from-literal=admin-password=cloudbeaver-admin-password \
    --from-literal=initial-data.conf='{
      adminName: "cbadmin",
      adminPassword: "cloudbeaver-admin-password",
      teams: [
        {
          subjectId: "admins",
          teamName: "Platform administrators",
          description: "Platform administrators with CloudBeaver admin access.",
          permissions: ["admin"]
        },
        {
          subjectId: "data-analyst",
          teamName: "CloudBeaver users",
          description: "Approved CloudBeaver browser users.",
          permissions: []
        }
      ]
    }'

  seed_secret dlh-keycloak-config-cli-env \
    --from-literal=LDAP_BIND_PASSWORD=local-directory-bind-password \
    --from-literal=KC_TRINO_CLIENT_SECRET=local-trino-client-secret \
    --from-literal=KC_SUPERSET_CLIENT_SECRET=local-superset-client-secret \
    --from-literal=KC_DATAHUB_CLIENT_SECRET=local-datahub-client-secret \
    --from-literal=KC_JUPYTERHUB_CLIENT_SECRET=local-jupyterhub-client-secret \
    --from-literal=KC_CLOUDBEAVER_CLIENT_SECRET=local-cloudbeaver-client-secret \
    --from-literal=KC_PREFECT_CLIENT_SECRET=local-prefect-client-secret \
    --from-literal=KC_PREFECT_AUTOMATION_CLIENT_SECRET=local-prefect-automation-client-secret

  seed_secret dlh-ranger-admin \
    --from-literal=rangerAdminPassword=admin123 \
    --from-literal=rangerUsersyncPassword=usersync123 \
    --from-literal=rangerTagsyncPassword=tagsync123

  seed_secret dlh-ranger-postgresql \
    --from-literal=password=rangerdb123 \
    --from-literal=postgres-password=rangerdbadmin123
}

capture_command() {
  local name="$1"
  shift

  if [[ -n "${ARTIFACT_DIR}" ]]; then
    {
      echo "## $*"
      echo
      "$@"
    } > "${ARTIFACT_DIR}/${name}.log" 2>&1 || true
  else
    "$@" || true
  fi
}

dump_diagnostics() {
  local exit_code=$?

  [[ ${exit_code} -eq 0 ]] && return

  echo "Smoke install failed; collecting Kubernetes diagnostics..." >&2

  if [[ -n "${ARTIFACT_DIR}" ]]; then
    mkdir -p "${ARTIFACT_DIR}"
  fi

  capture_command helm-status helm status "${RELEASE_NAME}" -n "${NAMESPACE}"
  capture_command helm-manifest helm get manifest "${RELEASE_NAME}" -n "${NAMESPACE}"
  capture_command kubectl-context kubectl config current-context
  capture_command kubectl-get-all kubectl get all -n "${NAMESPACE}" -o wide
  capture_command kubectl-get-events kubectl get events -n "${NAMESPACE}" --sort-by=.lastTimestamp
  capture_command kubectl-get-secrets kubectl get secrets -n "${NAMESPACE}"

  if kubectl get pods -n "${NAMESPACE}" --no-headers >/dev/null 2>&1; then
    local pod
    while IFS= read -r pod; do
      [[ -z "${pod}" ]] && continue
      capture_command "describe-${pod}" kubectl describe pod "${pod}" -n "${NAMESPACE}"
      capture_command "logs-${pod}" kubectl logs "${pod}" -n "${NAMESPACE}" --all-containers=true
      capture_command "logs-previous-${pod}" kubectl logs "${pod}" -n "${NAMESPACE}" --all-containers=true --previous
    done < <(kubectl get pods -n "${NAMESPACE}" -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}')
  fi

  return "${exit_code}"
}

trap dump_diagnostics ERR

if [[ "${SKIP_DEPENDENCY_UPDATE}" != "true" ]]; then
  ./scripts/helm/helm-dependency-update.sh
fi

if [[ "${RESET_RELEASE_STATE}" == "true" ]]; then
  reset_release_state
fi

if [[ "$(basename "${VALUES_FILE}")" == "values-local-auth.yaml" ]]; then
  seed_local_auth_demo_secrets
fi

run_with_retries 3 15 \
  helm upgrade --install "${RELEASE_NAME}" "${CHART_PATH}" \
    -n "${NAMESPACE}" \
    --create-namespace \
    -f "${VALUES_FILE}" \
    --wait \
    --timeout "${TIMEOUT}"

mapfile -t workloads < <(run_with_retries 3 5 kubectl get deployment -n "${NAMESPACE}" -o name)
mapfile -t jobs < <(run_with_retries 3 5 kubectl get job -n "${NAMESPACE}" -o name)

for workload in "${workloads[@]}"; do
  run_with_retries 3 10 kubectl rollout status "${workload}" -n "${NAMESPACE}" --timeout="${TIMEOUT}"
done

for job in "${jobs[@]}"; do
  run_with_retries 3 10 kubectl wait --for=condition=complete "${job}" -n "${NAMESPACE}" --timeout="${TIMEOUT}"
done

mapfile -t pods < <(run_with_retries 3 5 kubectl get pod -n "${NAMESPACE}" --field-selector=status.phase!=Succeeded,status.phase!=Failed -o name)

for pod in "${pods[@]}"; do
  run_with_retries 3 10 kubectl wait --for=condition=Ready "${pod}" -n "${NAMESPACE}" --timeout="${TIMEOUT}"
done

run_with_retries 3 5 kubectl get pods,svc -n "${NAMESPACE}"
