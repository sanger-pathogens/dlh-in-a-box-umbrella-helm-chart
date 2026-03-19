# Umbrella Templates

This directory contains the umbrella-only templates that glue upstream charts
together.

## What this directory owns

```mermaid
flowchart LR
  Helpers[_helpers.tpl] --> Labels[Shared naming and labels]
  Helpers --> FQDNs[DataHub prerequisite service FQDN helpers]
  Compat[datahub-prerequisites-compat.yaml] --> Services[ExternalName compatibility Services]
  Compat --> Secret[mysql-secrets Secret]
  Notes[NOTES.txt] --> Operators[Post-install operator guidance]
```

## File map

| File | Purpose |
| --- | --- |
| `_helpers.tpl` | Shared chart naming, labels, and DataHub prerequisite FQDN helpers |
| `datahub-prerequisites-compat.yaml` | Creates compatibility Services and a MySQL secret when DataHub is enabled |
| `NOTES.txt` | Prints a post-install summary and common port-forward commands |

## Maintainer note

This directory should stay small. If a template is not coordinating multiple
components or compensating for a release-level gap, it probably does not belong
in the umbrella chart.
