#!/usr/bin/env bash
set -euo pipefail

attempts="${HELM_DEPENDENCY_UPDATE_ATTEMPTS:-3}"
delay_seconds="${HELM_DEPENDENCY_UPDATE_RETRY_DELAY_SECONDS:-15}"

update_with_retry() {
  local chart_dir="$1"
  local attempt

  for ((attempt = 1; attempt <= attempts; attempt += 1)); do
    if helm dependency update "${chart_dir}"; then
      return 0
    fi

    if (( attempt == attempts )); then
      break
    fi

    echo "helm dependency update failed for ${chart_dir} on attempt ${attempt}/${attempts}; retrying in ${delay_seconds}s..." >&2
    sleep "${delay_seconds}"
  done

  echo "helm dependency update failed for ${chart_dir} after ${attempts} attempts." >&2
  return 1
}

# Helm does not resolve a subchart's own dependencies when the parent
# umbrella chart is updated -- each level of the dependency tree needs its
# own `helm dependency update`. Without this, a nested subchart with local
# dependencies of its own (e.g. shared-postgresql, which depends on the
# Bitnami postgresql chart) gets packaged with an empty `charts/` folder,
# silently dropping its templates from the umbrella chart with no error.
while IFS= read -r nested_chart_yaml; do
  if grep -q "^dependencies:" "${nested_chart_yaml}"; then
    update_with_retry "$(dirname "${nested_chart_yaml}")"
  fi
done < <(find charts/dlh-in-a-box/charts -mindepth 2 -maxdepth 2 -name "Chart.yaml" | sort)

update_with_retry charts/dlh-in-a-box
