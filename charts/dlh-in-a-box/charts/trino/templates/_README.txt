# Trino Template Patch Guide

This directory belongs to the vendored upstream Trino chart. Most files are
left exactly as upstream ships them. `dlh-in-a-box` only carries a small patch
set so the chart can generate catalog and access-control configuration from the
umbrella values model.

## Patch model

```mermaid
flowchart TD
  Upstream[Upstream Trino chart templates] --> LocalPatch[Small local patch set]
  LocalPatch --> Catalogs[Generated catalog ConfigMaps]
  LocalPatch --> AccessControl[Generated access-control ConfigMaps]
  LocalPatch --> Pods[Coordinator and worker mounts]
  Pods --> Runtime[Trino runtime]
```

## Files with local modifications

| File | Local purpose |
| --- | --- |
| `_helpers.tpl` | Shared helper behavior needed by the patched templates |
| `configmap-access-control-coordinator.yaml` | Generates access-control config for the coordinator |
| `configmap-catalog.yaml` | Generates Trino catalog configuration from `global.dataCatalogs` |
| `deployment-coordinator.yaml` | Mounts and wires the generated configuration into the coordinator |
| `deployment-worker.yaml` | Keeps worker wiring aligned with the local patch set |

All other templates should be assumed to be upstream until proven otherwise.

## Child guide

| Path | Guide | Purpose |
| --- | --- | --- |
| `tests/` | [tests/_README.txt](tests/_README.txt) | Helm tests bundled with the vendored Trino chart |

## Maintainer note

- Each modified file carries an explicit `Modified for dlh-in-a-box` notice.
- If the vendored Trino chart is refreshed from upstream, preserve the local
  patch set deliberately rather than re-applying changes ad hoc.
- The parent directory's [`../README.md`](../README.md) remains the upstream
  consumer-facing chart README.
