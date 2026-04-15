#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

missing=()

while IFS= read -r dir; do
  [[ "${dir}" == "${ROOT_DIR}" ]] && continue

  if [[ -f "${dir}/README.md" ]] || [[ -f "${dir}/README.md.gotmpl" ]] || [[ -f "${dir}/OVERVIEW.md" ]] || [[ -f "${dir}/_README.txt" ]]; then
    continue
  fi

  missing+=("${dir#${ROOT_DIR}/}")
done < <(
  find "${ROOT_DIR}" \
    \( -path "${ROOT_DIR}/.git" -o -path "${ROOT_DIR}/.idea" -o -path "${ROOT_DIR}/artifacts" -o -path "${ROOT_DIR}/dist" -o -path "${ROOT_DIR}/references" \) -prune -o \
    -type d -print | sort
)

if (( ${#missing[@]} > 0 )); then
  printf 'Missing directory guide file in:\n' >&2
  printf '  - %s\n' "${missing[@]}" >&2
  exit 1
fi

ruby <<'RUBY'
require "pathname"

root = Pathname.new(Dir.pwd)

markdown_files = Dir.glob("{README.md,charts/**/*.md,docs/**/*.md,examples/**/*.md,hack/**/*.md}")
  .reject { |path| path.include?("/third_party/") }
  .sort

required_headings = {
  "README.md" => ["## Start Here", "## Repository Mental Model", "## Default Platform Model"],
  "charts/dlh-in-a-box/README.md" => ["## What This Chart Does", "## Default Architecture", "## Governance And Policy"],
  "docs/auth-architecture.md" => ["## Default Model", "## Trino", "## Prefect"],
  "docs/data-governance.md" => ["## The Boundary", "## Governance Metadata Contract", "## New Data Source Rule"],
}

deprecated_patterns = {
  "phase-1 shared identity" => /phase-1 shared identity/i,
  "external OIDC as default" => /external OIDC IdP|external OIDC and LDAP-backed group resolution/i,
  "file ACLs as steady state" => /file-based ACLs\./i,
}

errors = []

markdown_files.each do |path|
  content = root.join(path).read
  fence_count = content.scan(/^```/).length
  if fence_count.odd?
    errors << "#{path}: unbalanced fenced code blocks"
  end

  content.scan(/\[[^\]]+\]\(([^)]+)\)/).flatten.each do |target|
    next if target.start_with?("http://", "https://", "mailto:", "#")

    clean = target.sub(/\A<|>\z/, "")
    clean = clean.split("#", 2).first
    next if clean.empty?

    resolved = root.join(File.dirname(path), clean).cleanpath
    errors << "#{path}: broken local link #{target}" unless resolved.exist?
  end

  if required_headings.key?(path)
    required_headings[path].each do |heading|
      errors << "#{path}: missing heading #{heading.inspect}" unless content.include?(heading)
    end
  end

  next unless ["README.md", "charts/dlh-in-a-box/README.md", "docs/auth-architecture.md"].include?(path)

  deprecated_patterns.each do |label, pattern|
    errors << "#{path}: deprecated wording detected for #{label}" if content.match?(pattern)
  end
end

if errors.any?
  warn errors.join("\n")
  exit 1
end
RUBY

if [[ "${SKIP_MERMAID_CHECK:-0}" != "1" ]]; then
  python3 "${ROOT_DIR}/hack/validate_mermaid.py" \
    --root "${ROOT_DIR}" \
    --include "README.md" \
    --include "charts/**/*.md" \
    --include "charts/**/_README.txt" \
    --include "docs/**/*.md" \
    --include "examples/**/*.md" \
    --include "hack/**/*.md" \
    --exclude "charts/dlh-in-a-box/third_party/**"
fi
