#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

search_with_fallback() {
  local pattern="${1:?pattern required}"
  shift

  if command -v rg >/dev/null 2>&1; then
    rg -n "${pattern}" "$@" || true
  else
    grep -RInE "${pattern}" "$@" || true
  fi
}

if grep -Eq '^kind: ConfigMap$' charts/dlh-in-a-box/charts/trino/templates/configmap-catalog.yaml; then
  echo "Trino catalog template must not render as a ConfigMap because it carries object-store credentials." >&2
  exit 1
fi

if grep -Eq '^kind: ConfigMap$' charts/dlh-in-a-box/charts/hive/templates/configmap.yaml; then
  echo "Hive metastore configuration template must not render as a ConfigMap because it carries database and object-store credentials." >&2
  exit 1
fi

for workflow in .github/workflows/*.yaml; do
  if grep -Eq 'uses: actions/checkout@v[0-9]+' "${workflow}"; then
    echo "Workflow ${workflow} must pin actions/checkout to an immutable commit SHA." >&2
    exit 1
  fi

  if grep -Eq 'uses: azure/setup-helm@v[0-9]+' "${workflow}"; then
    echo "Workflow ${workflow} must pin azure/setup-helm to an immutable commit SHA." >&2
    exit 1
  fi
done

non_local_examples=(
  "examples/values-dev.yaml"
  "examples/values-external-s3.yaml"
  "examples/values-minio.yaml"
  "examples/values-prod.yaml"
  "examples/values-prod-layers.yaml"
  "examples/values-shared-auth.yaml"
)

ruby - "${non_local_examples[@]}" <<'RUBY'
require "yaml"

def load_yaml(path)
  content = File.read(path)

  begin
    YAML.safe_load(content, aliases: true) || {}
  rescue ArgumentError
    YAML.load(content) || {}
  end
end

paths = {
  "global.storage.s3.accessKey" => %w[global storage s3 accessKey],
  "global.storage.s3.secretKey" => %w[global storage s3 secretKey],
  "datahubPrerequisites.mysql.auth.rootPassword" => %w[datahubPrerequisites mysql auth rootPassword],
  "hive.postgres.password" => %w[hive postgres password],
  "hive.s3.accessKey" => %w[hive s3 accessKey],
  "hive.s3.secretKey" => %w[hive s3 secretKey],
  "minio.auth.rootPassword" => %w[minio auth rootPassword],
  "hivePostgresql.auth.postgresPassword" => %w[hivePostgresql auth postgresPassword],
  "superset.extraSecretEnv.SUPERSET_SECRET_KEY" => %w[superset extraSecretEnv SUPERSET_SECRET_KEY],
  "superset.init.adminUser.password" => %w[superset init adminUser password],
  "superset.postgresql.auth.password" => %w[superset postgresql auth password],
  "superset.redis.auth.password" => %w[superset redis auth password],
  "superset.supersetNode.connections.db_pass" => %w[superset supersetNode connections db_pass]
}

ARGV.each do |path|
  data = load_yaml(path)
  hits = []

  paths.each do |label, segments|
    value = segments.reduce(data) do |memo, segment|
      memo.is_a?(Hash) ? memo[segment] : nil
    end

    hits << label if value.is_a?(String) && !value.empty?
  end

  next if hits.empty?

  warn "#{path} contains inline sensitive values outside the disposable local overlays:"
  hits.each { |hit| warn "  - #{hit}" }
  exit 1
end
RUBY

allowed_bitnamilegacy_paths=(
  "charts/dlh-in-a-box/values.yaml"
  "examples/values-local-auth.yaml"
  "examples/values-local.yaml"
  "examples/values-local-layers.yaml"
  "examples/values-local-superset.yaml"
)

while IFS=: read -r path _; do
  [[ -z "${path}" ]] && continue

  allowed=false
  for expected in "${allowed_bitnamilegacy_paths[@]}"; do
    if [[ "${path}" == "${expected}" ]]; then
      allowed=true
      break
    fi
  done

  if [[ "${allowed}" != "true" ]]; then
    echo "Unexpected bitnamilegacy image reference found in ${path}. Keep new references out of the chart until the temporary supply-chain debt is removed." >&2
    exit 1
  fi
done < <(search_with_fallback 'bitnamilegacy/' charts/dlh-in-a-box/values.yaml examples/*.yaml)
