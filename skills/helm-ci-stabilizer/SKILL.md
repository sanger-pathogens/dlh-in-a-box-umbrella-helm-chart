---
name: helm-ci-stabilizer
description: Use when debugging or fixing Helm Lint, Helm Publish, helm dependency update, GHCR chart publishing, or kind smoke-install failures in this repository, especially when GitHub Actions and local Helm behavior differ.
---

# Helm CI Stabilizer Skill

Use this skill for failures in:

- `.github/workflows/helm-lint.yaml`
- `.github/workflows/helm-publish.yaml`
- `.github/workflows/helm-smoke-install.yaml`
- `scripts/helm-dependency-update.sh`
- `scripts/lint.sh`
- `scripts/template.sh`
- `scripts/package.sh`
- `scripts/smoke-install.sh`

## First Moves

Resolve the failing workflow and exact failed step before editing:

```bash
git status --short --branch
git log --oneline --decorate -n 8
```

If `gh` is unavailable, use the GitHub Actions API to list runs and jobs:

```bash
curl -fsSL 'https://api.github.com/repos/sanger-pathogens/dlh-in-a-box-umbrella-helm-chart/actions/workflows/helm-lint.yaml/runs?per_page=5'
curl -fsSL 'https://api.github.com/repos/sanger-pathogens/dlh-in-a-box-umbrella-helm-chart/actions/runs/RUN_ID/jobs?per_page=100'
```

Logs may require authentication even when job metadata is public. Use step
metadata to decide which local script to reproduce.

## Local Parity

CI uses Helm `v3.12.0`. Prefer that version when reproducing.

Normal gate:

```bash
./scripts/helm-dependency-update.sh
./scripts/lint.sh
./scripts/template.sh
rm -rf dist
./scripts/package.sh
```

For smoke failures, use the workflow-equivalent path only when a Kubernetes
context or kind cluster is available:

```bash
./scripts/smoke-install.sh charts/dlh-in-a-box examples/values-local-auth.yaml
```

## Clean Helm State

Local Docker credential helpers can break OCI dependency downloads. If Helm
fails with `docker-credential-desktop` or a local registry-config problem, use a
temporary config:

```bash
tmp="$(mktemp -d)"
mkdir -p "${tmp}/docker" "${tmp}/registry"
printf '{}' > "${tmp}/registry/config.json"
DOCKER_CONFIG="${tmp}/docker" \
HELM_REGISTRY_CONFIG="${tmp}/registry/config.json" \
./scripts/helm-dependency-update.sh
```

Do not commit temporary Helm or Docker config.

## Failure Map

`Update dependencies`:

- inspect `Chart.yaml`, `Chart.lock`, and packaged archives
- retry with clean Helm registry config
- check OCI dependencies and GHCR/Docker Hub auth
- keep retry behavior in `scripts/helm-dependency-update.sh` if CI flakes

`Lint chart` or `Lint and license checks`:

- run `./hack/lint.sh`
- inspect `license-check.sh`, `docs-check.sh`, `security-check.sh`, and
  `render-contract.sh`
- stale validation-message expectations belong in render-contract fixtures, not
  in workflows

`Render chart`:

- run `./hack/template.sh`
- render only a failing overlay when known:
  `./hack/template.sh examples/values-dev.yaml`

`Package chart`:

- run `./hack/package.sh`
- check `Chart.yaml` version and chart dependency archives

`Push chart to GHCR`:

- tag releases must have `vX.Y.Z` matching `Chart.yaml`
- publication proof comes from the workflow success
- anonymous `helm show chart` may return `401 Unauthorized`; do not treat that
  alone as publish failure

`Mermaid`:

- local machines may skip Mermaid with `SKIP_MERMAID_CHECK=1`
- CI can still enforce Mermaid rendering if Docker is available

## Fix Discipline

- Fix local scripts first when workflow YAML simply calls those scripts.
- Keep workflow and local behavior aligned.
- Do not loosen security checks or action SHA pinning to get CI green.
- Report residual external constraints, such as GHCR package visibility or
  unavailable authenticated logs.
