#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

CHART_PATH="${1:-charts/dlh-in-a-box}"
VALUES_FILE="${2:-examples/values-local.yaml}"
RELEASE_NAME="${RELEASE_NAME:-dlh}"
NAMESPACE="${NAMESPACE:-data-lakehouse-local}"
TIMEOUT="${TIMEOUT:-20m}"
ARTIFACT_DIR="${ARTIFACT_DIR:-}"
SKIP_DEPENDENCY_UPDATE="${SKIP_DEPENDENCY_UPDATE:-false}"

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
  ./hack/helm-dependency-update.sh
fi

helm upgrade --install "${RELEASE_NAME}" "${CHART_PATH}" \
  -n "${NAMESPACE}" \
  --create-namespace \
  -f "${VALUES_FILE}" \
  --wait \
  --timeout "${TIMEOUT}"

mapfile -t workloads < <(kubectl get deployment -n "${NAMESPACE}" -o name)

for workload in "${workloads[@]}"; do
  kubectl rollout status "${workload}" -n "${NAMESPACE}" --timeout="${TIMEOUT}"
done

kubectl wait --for=condition=Ready pod --all -n "${NAMESPACE}" --timeout="${TIMEOUT}"

kubectl get pods,svc -n "${NAMESPACE}"
