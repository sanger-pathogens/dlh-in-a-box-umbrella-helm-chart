# Repo Scripts

This folder contains the local scripts that validate repo structure and enforce
compliance with repo policies.

## Script Behavior
### `docs-check.sh`

What it does:

- checks Markdown fence balance
- checks local Markdown links
- optionally renders Mermaid blocks with Docker via `repo/validate_mermaid.py`

Inputs it cares about:

- `README.md`
- `OVERVIEW.md`
- `_README.txt`
- other Markdown guides covered by the include patterns

Common failure modes:

- a local link target moved
- a Mermaid block is invalid

### `license-check.sh`

What it does:

- checks for required bundled notice and license files
- verifies dependencies in `Chart.lock` are documented in notice files
- enforces modification notices on the locally patched Trino files
- checks the Vault archive still contains its license

Run this when:

- changing dependency versions
- touching notices or provenance files
- refreshing vendored or packaged material

### `security-check.sh`

What it does:

- ensures secret-bearing templates do not accidentally render as ConfigMaps
- ensures important GitHub Actions are pinned to immutable SHAs
- prevents new `bitnamilegacy/` image references from spreading beyond the
  deliberately allowed places
- blocks inline secrets in non-local example overlays

This is not a full security audit. It is a focused set of repo-specific guard
rails.


### `validate_mermaid.py`

What it does:

- collects Markdown files from include globs
- finds Mermaid code fences
- uses Docker plus `minlag/mermaid-cli` to render them
- fails if a block cannot render

Why it matters:

- `docs-check.sh` relies on this for strict Mermaid verification
- local authors often hit this only when a diagram looks fine as text but is
  invalid for the renderer

Useful knobs from the actual script:

- `SKIP_MERMAID_CHECK=1` skips the renderer step from `repo/docs-check.sh`
- `MERMAID_STRICT=1` requires Mermaid rendering even outside CI
- `MERMAID_CLI_IMAGE` overrides the Docker image, default
  `minlag/mermaid-cli:10.9.1`
- `MERMAID_DOCKER_PROBE_TIMEOUT_SECONDS`,
  `MERMAID_IMAGE_PULL_TIMEOUT_SECONDS`, and
  `MERMAID_RENDER_TIMEOUT_SECONDS` tune timeout behavior
