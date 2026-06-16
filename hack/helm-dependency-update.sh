#!/usr/bin/env bash
set -euo pipefail

attempts="${HELM_DEPENDENCY_UPDATE_ATTEMPTS:-3}"
delay_seconds="${HELM_DEPENDENCY_UPDATE_RETRY_DELAY_SECONDS:-15}"

for ((attempt = 1; attempt <= attempts; attempt += 1)); do
  if helm dependency update charts/dlh-in-a-box; then
    exit 0
  fi

  if (( attempt == attempts )); then
    break
  fi

  echo "helm dependency update failed on attempt ${attempt}/${attempts}; retrying in ${delay_seconds}s..." >&2
  sleep "${delay_seconds}"
done

echo "helm dependency update failed after ${attempts} attempts." >&2
exit 1
