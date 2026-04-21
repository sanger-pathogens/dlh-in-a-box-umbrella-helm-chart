#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

missing=()

while IFS= read -r dir; do
  [[ "${dir}" == "${ROOT_DIR}" ]] && continue
  [[ "${dir}" == "${ROOT_DIR}/docs/Internal" ]] && continue
  [[ "${dir}" == "${ROOT_DIR}/docs/Internal/"* ]] && continue

  if [[ -f "${dir}/OVERVIEW.md" ]] || [[ -f "${dir}/README.md" ]] || [[ -f "${dir}/README.md.gotmpl" ]] || [[ -f "${dir}/_README.txt" ]]; then
    continue
  fi

  missing+=("${dir#${ROOT_DIR}/}")
done < <(
  find "${ROOT_DIR}" \
    \( -path "${ROOT_DIR}/.git" -o -path "${ROOT_DIR}/.idea" -o -path "${ROOT_DIR}/artifacts" -o -path "${ROOT_DIR}/dist" -o -path "${ROOT_DIR}/references" -o -path "${ROOT_DIR}/docs/Internal" -o -path "${ROOT_DIR}/__pycache__" -o -path "*/__pycache__" \) -prune -o \
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

markdown_files = Dir.glob("{README.md,CONTRIBUTING.md,SUPPORT.md,.github/**/*.md,.vscode/**/*.md,charts/**/*.md,docs/**/*.md,examples/**/*.md,hack/**/*.md}")
  .sort
  .reject { |path| path == "docs/Internal/README.md" || path.start_with?("docs/Internal/") }

guide_files = []

Dir.glob("**/", File::FNM_DOTMATCH).sort.each do |dir|
  dir = dir.sub(%r{/\z}, "")
  next if dir.empty? || dir == "."
  next if dir.start_with?(".git/", ".idea/", "artifacts/", "dist/", "references/")
  next if dir == "docs/Internal" || dir.start_with?("docs/Internal/")
  next if dir.include?("/__pycache__")

  guide = ["OVERVIEW.md", "README.md", "README.md.gotmpl", "_README.txt"]
    .map { |name| File.join(dir, name) }
    .find { |path| File.exist?(path) }

  guide_files << guide if guide
end

guide_files << "README.md" if File.exist?("README.md")
guide_files.uniq!

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
