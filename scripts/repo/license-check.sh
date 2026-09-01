#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

required_files=(
  "THIRD_PARTY_NOTICES.md"
  "charts/dlh-in-a-box/THIRD_PARTY_NOTICES.md"
  "charts/dlh-in-a-box/LICENSE"
  "charts/dlh-in-a-box/charts/trino/LICENSE"
  "charts/dlh-in-a-box/third_party/datahub/NOTICE"
  "charts/dlh-in-a-box/third_party/gcloud-sqlproxy/LICENSE"
  "charts/dlh-in-a-box/third_party/oauth2-proxy/LICENSE"
)

for file in "${required_files[@]}"; do
  if [[ ! -f "${file}" ]]; then
    echo "Missing required licensing file: ${file}" >&2
    exit 1
  fi
done

# A dependency's own Chart.yaml `home` field tells apart chart-owned
# (first-party) subcharts, which point back at this repo, from genuinely
# third-party ones, which point at their own upstream project -- vendoring
# a chart locally (file:// repository) doesn't by itself mean it's ours
# (e.g. trino is vendored too). Only genuinely third-party dependencies
# need a THIRD_PARTY_NOTICES.md entry.
own_home="$(yq eval '.home' charts/dlh-in-a-box/Chart.yaml)"
deps="$(
  yq eval '.dependencies[] | [.name, .repository] | @tsv' charts/dlh-in-a-box/Chart.lock |
  while IFS=$'\t' read -r name repository; do
    subchart_dir="${repository#file://}"
    subchart_home="$(yq eval '.home' "charts/dlh-in-a-box/${subchart_dir}/Chart.yaml" 2>/dev/null)"
    if [[ "${subchart_home}" == "${own_home}" ]]; then
      continue
    fi
    echo "${name}"
  done
)"

for doc in "THIRD_PARTY_NOTICES.md" "charts/dlh-in-a-box/THIRD_PARTY_NOTICES.md"; do
  while IFS= read -r dep; do
    [[ -n "${dep}" ]] || continue
    if ! grep -Fq "${dep}" "${doc}"; then
      echo "Dependency '${dep}' is not documented in ${doc}" >&2
      exit 1
    fi
  done <<< "${deps}"
done

modified_trino_files=(
  "charts/dlh-in-a-box/charts/trino/templates/_helpers.tpl"
  "charts/dlh-in-a-box/charts/trino/templates/configmap-access-control-coordinator.yaml"
  "charts/dlh-in-a-box/charts/trino/templates/configmap-catalog.yaml"
  "charts/dlh-in-a-box/charts/trino/templates/deployment-coordinator.yaml"
  "charts/dlh-in-a-box/charts/trino/templates/deployment-worker.yaml"
)

for file in "${modified_trino_files[@]}"; do
  if ! grep -Fq "Modified for dlh-in-a-box" "${file}"; then
    echo "Missing modification notice in ${file}" >&2
    exit 1
  fi
done

shopt -s nullglob
vault_archives=(charts/dlh-in-a-box/charts/vault-*.tgz)
shopt -u nullglob
if (( ${#vault_archives[@]} > 0 )); then
  archive_index="$(mktemp)"
  trap 'rm -f "${archive_index}"' EXIT
  tar -tzf "${vault_archives[0]}" > "${archive_index}"
  if ! grep -Fqx "vault/LICENSE" "${archive_index}"; then
    echo "Vault dependency archive no longer contains vault/LICENSE" >&2
    exit 1
  fi
  rm -f "${archive_index}"
  trap - EXIT
fi
