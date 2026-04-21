# Trino Helm Tests

This folder contains the Helm tests that ship with the vendored upstream
Trino chart.

```mermaid
flowchart LR
  TestFiles[Test files] --> HelmTest[helm test]
  HelmTest --> BasicChecks[Basic Trino checks]
```

## What these tests cover

| File | Plain meaning |
| --- | --- |
| `test-connection.yaml` | Basic service reachability test |
| `test-graceful-shutdown.yaml` | Graceful shutdown behavior |
| `test-jmx.yaml` | JMX metrics surface |
| `test-networkpolicy.yaml` | Network policy behavior where applicable |

## When you can ignore this folder

You can ignore this folder unless you are changing Trino tests.

## Common mistake

These tests are upstream coverage. Avoid changing them unless the local Trino
patch set truly needs it.
