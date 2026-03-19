#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

missing=()

while IFS= read -r dir; do
  [[ "${dir}" == "${ROOT_DIR}" ]] && continue

  if [[ -f "${dir}/README.md" ]] || [[ -f "${dir}/README.md.gotmpl" ]] || [[ -f "${dir}/_README.txt" ]]; then
    continue
  fi

  missing+=("${dir#${ROOT_DIR}/}")
done < <(
  find "${ROOT_DIR}" \
    \( -path "${ROOT_DIR}/.git" -o -path "${ROOT_DIR}/dist" \) -prune -o \
    -type d -print | sort
)

if (( ${#missing[@]} > 0 )); then
  printf 'Missing directory guide file in:\n' >&2
  printf '  - %s\n' "${missing[@]}" >&2
  exit 1
fi
