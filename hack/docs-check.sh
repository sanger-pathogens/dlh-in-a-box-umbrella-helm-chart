#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

DOCS_CHECK_IGNORE=(
  .git
  .idea
  artifacts
  dist
  references
  "docs/Internal"
  __pycache__
  node_modules
  "tmpcharts-*"
)

# Build find(1) -prune arguments.
prune_args=()
for pat in "${DOCS_CHECK_IGNORE[@]}"; do
  [[ ${#prune_args[@]} -gt 0 ]] && prune_args+=(-o)
  if [[ "$pat" == */* ]]; then
    prune_args+=(-path "${ROOT_DIR}/${pat}")
  elif [[ "$pat" == *'*'* ]]; then
    prune_args+=(-path "*/${pat}")
  else
    prune_args+=(-path "${ROOT_DIR}/${pat}" -o -path "*/${pat}")
  fi
done

# Export space-separated list for the Ruby block below.
export DOCS_CHECK_IGNORE_LIST="${DOCS_CHECK_IGNORE[*]}"

missing=()

while IFS= read -r dir; do
  [[ "${dir}" == "${ROOT_DIR}" ]] && continue

  if [[ -f "${dir}/OVERVIEW.md" ]] || [[ -f "${dir}/README.md" ]] || [[ -f "${dir}/README.md.gotmpl" ]] || [[ -f "${dir}/_README.txt" ]]; then
    continue
  fi

  missing+=("${dir#${ROOT_DIR}/}")
done < <(
  find "${ROOT_DIR}" \
    \( "${prune_args[@]}" \) -prune -o \
    -type d -print | sort
)

if (( ${#missing[@]} > 0 )); then
  printf 'Missing directory guide file in:\n' >&2
  printf '  - %s\n' "${missing[@]}" >&2
  exit 1
fi

ruby <<'RUBY'
require "find"
require "pathname"

root = Pathname.new(Dir.pwd)
ignore_patterns = ENV.fetch('DOCS_CHECK_IGNORE_LIST', '').split

# Check for ignored paths
def docs_ignored?(path, patterns)
  parts = path.split('/')
  (1..parts.length).any? do |n|
    segment = parts[0, n].join('/')
    patterns.any? do |pat|
      if pat.include?('/')
        segment == pat
      elsif pat.include?('*')
        File.fnmatch(pat, parts[n - 1])
      else
        parts[n - 1] == pat
      end
    end
  end
end

markdown_files = []
guide_files = []

Find.find(".") do |path|
  rel = path.delete_prefix("./")
  next if rel.empty? || rel == "."

  if File.directory?(path)
    if docs_ignored?(rel, ignore_patterns)
      Find.prune
    else
      guide = ["OVERVIEW.md", "README.md", "README.md.gotmpl", "_README.txt"]
        .map { |name| File.join(rel, name) }
        .find { |p| File.exist?(p) }
      guide_files << guide if guide
    end
  elsif File.file?(path)
    if rel.end_with?(".md") && !docs_ignored?(rel, ignore_patterns)
      markdown_files << rel
    end
  end
end

guide_files << "README.md" if File.exist?("README.md")
guide_files.uniq!
markdown_files.sort!

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
end

guide_files.each do |path|
  next if path.end_with?(".gotmpl")

  content = root.join(path).read
  unless content.include?("```mermaid")
    errors << "#{path}: missing Mermaid diagram in guide file"
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
    --include ".github/**/*.md" \
    --include ".vscode/**/*.md" \
    --include "charts/**/*.md" \
    --include "charts/**/_README.txt" \
    --include "docs/**/*.md" \
    --include "examples/**/*.md" \
    --include "hack/**/*.md"
fi
