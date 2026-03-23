# Documentation

This directory holds repository-owned onboarding, release, and static
documentation assets.

## Current structure

```mermaid
flowchart LR
  Docs[docs/] --> Assets[docs/assets]
  Docs --> Auth[auth-architecture.md]
  Docs --> Quickstart[quickstart.md]
  Docs --> Release[release-playbook.md]
  Assets --> Icon[dlh-in-a-box icon]
  Icon --> ChartMetadata[Chart.yaml icon metadata]
  Icon --> Readme[README and package presentation]
```

## Child guide

| Path | Guide | Purpose |
| --- | --- | --- |
| `quickstart.md` | [quickstart.md](quickstart.md) | First-run onboarding for new consumers |
| `auth-architecture.md` | [auth-architecture.md](auth-architecture.md) | Shared identity, groups, and access-control design |
| `release-playbook.md` | [release-playbook.md](release-playbook.md) | Release and publication runbook |
| `assets/` | [assets/README.md](assets/README.md) | Static icons and future documentation assets |

## Maintainer note

This directory is where narrative documentation should live when it is too long
or too operational to belong in the root README or chart README.
