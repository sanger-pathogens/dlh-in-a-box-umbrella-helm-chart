# Trino Helm Tests

This directory contains the Helm tests that ship with the vendored upstream
Trino chart.

## What these tests cover

| File | Purpose |
| --- | --- |
| `test-connection.yaml` | Basic service reachability test |
| `test-graceful-shutdown.yaml` | Shutdown behavior validation |
| `test-jmx.yaml` | JMX surface validation |
| `test-networkpolicy.yaml` | Network policy validation where applicable |

## Maintainer note

These tests are primarily upstream coverage. Treat them as part of the vendor
surface and avoid changing them unless the local Trino patch set genuinely
requires it.
