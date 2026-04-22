# Trino Helm Tests

This folder contains the Helm tests that ship with the vendored upstream Trino
chart.

These files are not the main repo-specific validation path. The repo mostly
validates Trino through `render-contract.sh`, `template.sh`, and `lint.sh`.
Still, the Helm tests matter because they document the runtime assumptions the
vendored chart expects to hold.

## Who Should Read This

| Reader | Why this guide matters |
| --- | --- |
| contributor | to understand what the upstream chart considers basic runtime health |
| maintainer | to know what might need review when refreshing the vendored Trino chart |

```mermaid
flowchart TD
  subgraph Inputs["Helm test inputs"]
    Release[rendered Trino release]
    Services[services and probes]
    Policy[network policy and metrics surface]
  end

  subgraph Tests["Upstream Helm tests"]
    Connection[test connection]
    Shutdown[test graceful shutdown]
    Jmx[test jmx]
    Network[test networkpolicy]
  end

  subgraph Outcome["What they prove"]
    Reachability[basic reachability]
    Drain[graceful drain path]
    Metrics[jmx exposure]
    Isolation[network policy behavior]
  end

  Release --> Connection --> Reachability
  Release --> Shutdown --> Drain
  Services --> Jmx --> Metrics
  Policy --> Network --> Isolation
```

## What Lives In This Folder

| File | Ownership | What it checks |
| --- | --- | --- |
| `test-connection.yaml` | upstream | basic coordinator reachability |
| `test-graceful-shutdown.yaml` | upstream | worker graceful shutdown behavior when that feature is enabled |
| `test-jmx.yaml` | upstream | JMX endpoint exposure |
| `test-networkpolicy.yaml` | upstream | network-policy assumptions where applicable |
| `_README.txt` | repo-owned guide | this explanation layer |

## How To Think About These Tests

These are smoke-like Helm tests attached to the vendored Trino chart, not a
full functional test suite.

They answer questions such as:

- can the chart's service be reached
- does graceful shutdown wiring still exist
- is the JMX surface there when enabled
- does the network policy still allow the expected test path

They do not replace the repo's contract tests for auth and governance.

## When To Change Them

Change these tests only when one of the following is true:

- the vendored upstream chart changed and the tests need to stay aligned
- a deliberate local Trino patch changes one of the runtime assumptions the
  upstream test depends on

If the bug or feature is really about generated catalogs, identity wiring, or
Ranger integration, the change usually belongs outside this folder.

## Validation

The normal repo validation commands are still:

```bash
./hack/render-contract.sh
./hack/template.sh
./hack/lint.sh
```

If you do change these tests, also review the rendered Helm test manifests so
the test container commands still match the runtime shape.

## Common Mistakes

- changing an upstream test when the real bug is in a Trino runtime template
- expecting these files to cover the repo's identity and governance contract
- forgetting that Helm tests can lag or change when the vendored chart is
  refreshed

## When You Can Ignore This Folder

You can ignore this folder unless you are changing Helm test coverage or
refreshing the vendored Trino chart.
