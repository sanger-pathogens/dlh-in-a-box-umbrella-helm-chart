# Umbrella Templates

This directory contains the chart-owned templates that do not belong inside a
single upstream dependency.

If a behavior is specific to `dlh-in-a-box` rather than to Trino, Hive,
Keycloak, or another dependency chart, it usually lands here.

## What this directory owns

```mermaid
flowchart LR
  Helpers[_helpers.tpl and _ranger-admin.tpl] --> Shared[shared helper logic]
  Validation[identity-validation plus governance-validation] --> Contract[chart contract checks]
  Portal[platform-home.yaml] --> Browser[launchpad and admin API]
  CloudBeaver[cloudbeaver.yaml] --> Browser
  Ranger[ranger-admin.yaml plus ranger-automation.yaml plus ranger-browser-proxy.yaml] --> Governance[role and policy automation]
  DataHub[datahub-auth-secrets plus datahub-prerequisites-compat] --> Compat[compatibility glue]
  Notes[NOTES.txt] --> Output[post-install guidance]
```

## File map

| File | Purpose |
| --- | --- |
| `_helpers.tpl` | Shared naming, labels, and helper functions |
| `_ranger-admin.tpl` | Shared Ranger admin helper logic |
| `identity-validation.yaml` | Enforces supported identity contract combinations |
| `governance-validation.yaml` | Enforces governance metadata and policy coverage rules |
| `platform-home.yaml` | Launchpad frontend, admin API, ConfigMaps, RBAC, CronJob, and ingress |
| `cloudbeaver.yaml` | CloudBeaver deployment, config, seeded workspace support, and optional trust-store wiring |
| `ranger-admin.yaml` | Ranger admin deployment and related resources |
| `ranger-automation.yaml` | Ranger bootstrap, usersync helpers, local-user sync, and exception audit jobs |
| `ranger-browser-proxy.yaml` | Optional Ranger browser auth proxy resources |
| `datahub-auth-secrets.yaml` | DataHub auth-related Secret helpers |
| `datahub-prerequisites-compat.yaml` | Compatibility resources for DataHub prerequisite expectations |
| `NOTES.txt` | Post-install summary and common local access commands |

## Maintainer note

This directory should stay focused on true umbrella logic. If a change belongs
inside an upstream dependency or local subchart instead, prefer that home.
