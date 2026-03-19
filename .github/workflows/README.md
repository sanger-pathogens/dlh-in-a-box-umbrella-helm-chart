# GitHub Actions Workflows

This directory contains the automation that validates and publishes the chart.

## Workflow inventory

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| `helm-lint.yaml` | `push`, `pull_request` | Dependency refresh, docs checks, schema validation, lint, render, and package verification |
| `helm-publish.yaml` | `push` to `main`, `push` tags `v*`, `workflow_dispatch` | Version resolution, packaging, GHCR login, and OCI publication |

## Workflow lifecycle

```mermaid
flowchart TD
  Push[Push or pull request] --> Lint[helm-lint workflow]
  Lint --> DependencyUpdate[helm dependency update]
  DependencyUpdate --> DocsChecks[directory guide and script checks]
  DocsChecks --> LicenseChecks[license and notice checks]
  LicenseChecks --> Render[helm template]
  Render --> Package[helm package]

  MainPush[Push to main] --> Publish[helm-publish workflow]
  TagPush[Push tag vX.Y.Z] --> Publish
  Publish --> ResolveVersion[resolve release or prerelease version]
  ResolveVersion --> GHCRLogin[log in to GHCR]
  GHCRLogin --> PushArtifact[push OCI chart artifact]
  PushArtifact --> ConsumerRepos[consumer repositories]
```

## Publication behavior

- `main` publishes a unique prerelease version:
  `<base-version>-main.<run-number>.<run-attempt>.<short-sha>`
- `vX.Y.Z` tags publish the stable `X.Y.Z` version and fail if the Git tag does
  not match `charts/dlh-in-a-box/Chart.yaml`
- GHCR authentication uses `GITHUB_TOKEN` by default, with optional `GHCR_TOKEN`
  and `GHCR_USERNAME` overrides if organization policy requires them

## Operational expectations

- Keep workflow logic aligned with the scripts under [`../../hack/README.md`](../../hack/README.md)
  so local validation and CI validation do not drift apart.
- If new example overlays are added, they should be covered by the maintainer
  scripts and therefore by `helm-lint`.
- If package publication rules change, update the root README and
  [`../../charts/dlh-in-a-box/README.md`](../../charts/dlh-in-a-box/README.md)
  so downstream consumers see the same contract.
