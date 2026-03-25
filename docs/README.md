# Documentation

This directory holds the long-form documentation for the chart repository.

Use it when the chart README has already told you where to start, but you now
need the deeper explanation behind the values contract or the default platform
model.

## Read In This Order

1. [../README.md](../README.md)
2. [../charts/dlh-in-a-box/README.md](../charts/dlh-in-a-box/README.md)
3. [quickstart.md](quickstart.md)
4. [glossary.md](glossary.md)
5. [auth-architecture.md](auth-architecture.md)
6. [data-governance.md](data-governance.md)
7. [release-playbook.md](release-playbook.md)

## What Lives Here

| File | Purpose |
| --- | --- |
| `quickstart.md` | Fastest route from inspection to install |
| `glossary.md` | Definitions for the terms used across the chart docs |
| `auth-architecture.md` | Default Keycloak, LDAP/AD, Ranger, and Prefect access model |
| `data-governance.md` | Governance metadata contract and policy-compliance boundary |
| `release-playbook.md` | Maintainer-oriented release and publication workflow |
| `assets/` | Static images and branding assets used by the repo |

## Documentation Rules

- Primary docs explain the default path first.
- Escape hatches are documented, but not presented as the main story.
- Vendored upstream docs are reference-only.
- The docs say clearly when Helm enforces something and when a human approval
  process is still required.
