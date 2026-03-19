# Maintainer Scripts

This directory contains the repeatable local scripts used for dependency
refresh, validation, packaging, and release preparation.

## Script flow

```mermaid
flowchart LR
  Update[helm-dependency-update.sh] --> Lint[lint.sh]
  Docs[docs-check.sh] --> Lint
  Lint --> Render[template.sh]
  Render --> Package[package.sh]
  Lint --> Publish[GitHub publish workflow]
  Package --> Publish
```

## Script inventory

| Script | Purpose |
| --- | --- |
| `docs-check.sh` | Verify that maintained directories still carry local guide files |
| `helm-dependency-update.sh` | Refresh `Chart.lock` and packaged dependencies |
| `license-check.sh` | Verify required notice files and local vendor modification markers |
| `lint.sh` | Run docs, script, schema, license, and Helm lint checks against every example overlay |
| `template.sh` | Render the chart against every example overlay or a supplied subset |
| `package.sh` | Package the chart, optionally overriding chart and app versions |

## Typical maintainer sequence

```bash
./hack/helm-dependency-update.sh
./hack/lint.sh
./hack/template.sh
./hack/package.sh
```

Equivalent convenience targets are also available through `make` at the
repository root.

## Maintainer note

Keep these scripts aligned with GitHub Actions. They are meant to be the local
mirror of what CI and publication automation expect, not a separate workflow.
