# Trino Helm Tests

This directory contains the Helm tests that ship with the vendored upstream
Trino chart.

## What these tests cover

| File | Purpose |
| --- | --- |
| `test-connection.yaml` | Basic service reachability test |
| `test-graceful-shutdown.yaml` | Graceful shutdown behavior |
| `test-jmx.yaml` | JMX metrics surface |
| `test-networkpolicy.yaml` | Network policy behavior where applicable |

## Maintainer note

These tests are upstream coverage. Avoid changing them unless the local Trino
patch set genuinely requires it.
