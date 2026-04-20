# Trino Template Patch Guide

This directory belongs to the vendored upstream Trino chart.

Most files are kept as upstream reference material. `dlh-in-a-box` carries only
the local patches needed to connect the Trino chart to the umbrella values
model.

## Patch model

```mermaid
flowchart TD
  Upstream[Upstream Trino templates] --> LocalPatch[Small local patch set]
  LocalPatch --> Catalogs[Generated catalog config]
  LocalPatch --> AccessControl[Generated access-control config]
  LocalPatch --> Pods[Coordinator and worker mounts]
```

## Files with local modifications

| File | Local purpose |
| --- | --- |
| `_helpers.tpl` | Helper behavior needed by the patched templates |
| `configmap-access-control-coordinator.yaml` | Generated access-control config for the coordinator |
| `configmap-catalog.yaml` | Generated Trino catalog config from `global.dataCatalogs` |
| `deployment-coordinator.yaml` | Mounts and wires generated config into the coordinator |
| `deployment-worker.yaml` | Keeps worker wiring aligned with the generated config model |

All other files should be assumed to be upstream unless you see a deliberate
local change notice.

## Child guide

| Path | Guide | Purpose |
| --- | --- | --- |
| `tests/` | [tests/_README.txt](tests/_README.txt) | Helm tests shipped with the vendored Trino chart |

## Maintainer note

- Each local patch file carries an explicit `Modified for dlh-in-a-box` notice.
- If the vendored Trino chart is refreshed, preserve the patch set
  deliberately instead of re-applying changes ad hoc.
- The parent [../README.md](../README.md) is the upstream consumer README and
  should be treated as reference material.
