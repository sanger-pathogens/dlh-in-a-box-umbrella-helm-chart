# Trino Template Patch Guide

This folder contains the Trino render files.

Most of this folder is upstream Trino chart code.

This repo adds only a small local patch set so Trino fits the umbrella chart.

## Patch model

```mermaid
flowchart TD
  Upstream[Upstream Trino templates] --> LocalPatch[Small local changes]
  LocalPatch --> Catalogs[Generated catalog config]
  LocalPatch --> Access[Generated access config]
  LocalPatch --> Pods[Pod mounts and wiring]
```

## Files with local modifications

| File | Plain meaning |
| --- | --- |
| `_helpers.tpl` | Helper behavior needed by the patched templates |
| `configmap-access-control-coordinator.yaml` | Generated access-control config for the coordinator |
| `configmap-catalog.yaml` | Generated Trino catalog config from `global.dataCatalogs` |
| `deployment-coordinator.yaml` | Mounts and wires generated config into the coordinator |
| `deployment-worker.yaml` | Keeps worker wiring aligned with the generated config model |

All other files should be assumed to be upstream unless you see a deliberate
local change notice.

## When you can ignore this folder

You can ignore this folder unless you are changing Trino internals.

## Common mistakes

- changing an upstream file without noticing it is upstream
- forgetting to preserve the local patch set when the vendored Trino chart is
  refreshed
