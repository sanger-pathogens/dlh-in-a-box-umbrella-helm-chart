# Trino Template Patch Guide

This folder contains the Trino render templates for the vendored chart.

Most files are upstream chart material. A smaller set carries the repo's local
catalog, auth, and rollout integration behavior.

## Who Should Read This

| Reader | Why this guide matters |
| --- | --- |
| contributor | to know which Trino template actually owns the behavior being changed |
| operator | to understand where OIDC, password auth, generated catalogs, and file or Ranger access-control are wired |
| maintainer | to safely refresh the vendored chart without losing the local patch set |

## Patch Model

```mermaid
flowchart TD
  subgraph Inputs["Platform inputs"]
    Catalogs[global dataCatalogs]
    Identity[shared identity values]
    Authorization[shared authorization values]
    Secrets[existing and generated secrets]
  end

  subgraph Templates["Trino templates"]
    Local[local patch points]
    Upstream[upstream runtime templates]
  end

  subgraph Runtime["Rendered outcome"]
    Coordinator[coordinator pod]
    Workers[worker pods]
    Services[services ingress and metrics]
  end

  Catalogs --> Local
  Identity --> Local
  Identity --> Upstream
  Authorization --> Local
  Authorization --> Upstream
  Secrets --> Local
  Secrets --> Upstream
  Local --> Coordinator
  Local --> Workers
  Upstream --> Coordinator
  Upstream --> Workers
  Upstream --> Services
```

## What Lives In This Folder

| File or path | Ownership status | Why it matters |
| --- | --- | --- |
| `_helpers.tpl` | locally modified | helper additions for generated catalogs, secret lookups, and access-control rules |
| `configmap-access-control-coordinator.yaml` | locally modified | generated file-based coordinator access rules when Ranger plugin is not active |
| `configmap-catalog.yaml` | locally modified | generated per-catalog Trino properties from the umbrella catalog contract |
| `deployment-coordinator.yaml` | locally modified | mounts generated config and injects shared identity secrets into the coordinator |
| `deployment-worker.yaml` | locally modified | mounts generated config and shared secret into workers |
| `configmap-coordinator.yaml` | behaviorally critical vendored snapshot file | writes coordinator config including OIDC, optional password auth, and Ranger plugin wiring |
| `configmap-access-control-worker.yaml` | upstream but behaviorally relevant | graceful-shutdown worker access-control rules |
| `configmap-worker.yaml` | upstream but behaviorally relevant | worker config and internal shared-secret wiring |
| `configmap-jmx-exporter.yaml` | upstream | JMX exporter config for metrics exposure |
| `secret.yaml` | upstream but behaviorally relevant | file-password and group database secret generation |
| `service-coordinator.yaml` | upstream but behaviorally relevant | coordinator Service ports including optional JMX and extra ports |
| `service-worker.yaml` | upstream | worker Service wiring |
| `serviceaccount.yaml` | upstream | service account creation and naming |
| `ingress.yaml` | upstream | optional ingress exposure |
| `networkpolicy.yaml` | upstream | optional network policy objects |
| `autoscaler.yaml` | upstream | worker autoscaling resources |
| `servicemonitor-coordinator.yaml` | upstream | Prometheus ServiceMonitor for the coordinator |
| `servicemonitor-worker.yaml` | upstream | Prometheus ServiceMonitor for workers |
| `NOTES.txt` | upstream | post-install access hints |
| `tests/` | upstream tests plus local guide | Helm test coverage for connection, JMX, network policy, and graceful shutdown |

## Where Auth, Access Control, And Catalog Wiring Actually Happen

This is the part newcomers usually need most.

### Catalog generation

Catalog generation is the repo-specific layer that turns
`global.dataCatalogs` into Trino catalog property files.

The flow is:

1. `_helpers.tpl` resolves the shared catalog and S3 settings
2. `configmap-catalog.yaml` renders one `*.properties` file per catalog
3. `deployment-coordinator.yaml` and `deployment-worker.yaml` mount that
   generated secret under Trino's catalog directory

Without these files, the umbrella chart would not turn shared catalog metadata
into queryable Trino catalogs.

One important subtlety from the code:

- `_helpers.tpl` can use Helm `lookup` to read S3 credentials from
  `global.storage.s3.existingSecret`
- that means a render done against a cluster with the secret present can differ
  from an offline `helm template` where that secret is absent
- if the secret does not exist at render time, the generated catalog properties
  can end up with empty credential values rather than the inline-value path

### Coordinator auth

`configmap-coordinator.yaml` is the coordinator control center.

In the current vendored snapshot it writes:

- OIDC issuer and token endpoints
- client ID and secret references
- optional mixed `OAUTH2,PASSWORD` mode when the shared identity contract says
  password auth is allowed
- LDAP password-auth settings when that mode is selected
- Ranger plugin configuration when Ranger-backed Trino authorization is enabled
- fallback upstream settings when shared identity is not enabled

This is also where some Trino-specific fail-fast checks still live, such as
missing identity secrets or unsupported auth combinations.

### File-based versus Ranger-backed authorization

The repo supports two broad authorization shapes:

- generated file-based rules
- Ranger plugin integration

`configmap-access-control-coordinator.yaml` renders file-based `rules.json`
when:

- Trino access control type is `configmap`
- Ranger plugin mode is not active

If the user supplies `accessControl.rules.rules.json`, that content is used.
Otherwise the template falls back to generated rules from helper logic.

When Ranger plugin mode is active, `configmap-coordinator.yaml` instead writes
`access-control.properties` and Ranger XML config so the coordinator queries
Ranger for policy decisions.

Worker nodes never use Ranger for full access decisions. Their separate
`configmap-access-control-worker.yaml` exists only to support graceful shutdown
rules.

### Secret wiring

Secret behavior is split across several files:

- `secret.yaml` handles upstream file-password and group database secrets
- `deployment-coordinator.yaml` injects OIDC client secret, internal shared
  secret, and LDAP bind password when shared identity is enabled
- `deployment-worker.yaml` injects the internal shared secret for node-to-node
  communication

This is why auth changes often touch both config and Deployment templates.

## Local Patch Points

### `_helpers.tpl`

The helper file carries the repo's main Trino-specific additions:

- shared catalog lookup from `global.dataCatalogs`
- S3 secret and inline-value resolution for generated catalogs
- catalog name sanitization
- generated access-control helper logic used by the coordinator rules template

Whenever the same repo-specific logic appears to belong in several templates,
it usually belongs here instead.

### `configmap-access-control-coordinator.yaml`

This file renders the coordinator `rules.json` only when Trino is using
file-based access control.

It is the bridge between:

- user-provided explicit access-control rules
- repo-generated default rules when no explicit file is supplied

If a contributor wants to change the generated file-based policy model without
turning on Ranger, this is the file to inspect.

### `configmap-catalog.yaml`

This template is the Trino side of the shared catalog contract.

It creates a secret containing one catalog properties file per catalog and
pulls shared S3 settings from the umbrella values.

This is what connects Trino to the Hive Metastore services generated by the
local Hive subchart.

It intentionally renders a `Secret`, not a `ConfigMap`, because the generated
catalog property files may contain object-store credentials.

### `deployment-coordinator.yaml`

This file adds the runtime shell required to make the generated config useful.

Important local behavior here includes:

- checksum rollouts for generated catalog and access-control config
- mounting generated catalog and access-control volumes
- mounting LDAP trust material when directory integration uses a custom CA
- injecting OIDC client secret and internal shared secret environment variables
- injecting LDAP bind password when directory-backed password auth is enabled

### `deployment-worker.yaml`

This file keeps workers aligned with the coordinator's generated config model.

Important local behavior includes:

- mounting generated catalog config
- checksum rollouts when catalogs change
- mounting graceful-shutdown access-control rules when that feature is enabled
- injecting the internal shared secret when shared identity is enabled

## Behaviorally Important Upstream Files

### `configmap-coordinator.yaml`

Even though this file is part of the vendored chart snapshot, it is one of the
most important files for understanding the deployed Trino behavior in this
repo.

If you need to answer "Why is Trino doing OIDC, LDAP password auth, or Ranger
plugin integration this way?", start here.

### `configmap-access-control-worker.yaml`

This file exists for graceful shutdown only.

It renders a minimal worker-side file access-control config that allows the
shutdown path to do the writes it needs during drain behavior.

It is not the general authorization policy engine for the cluster.

### `configmap-worker.yaml`

This file writes the worker JVM and `config.properties` content, including the
internal communication shared secret and optional graceful-shutdown settings.

### `service-coordinator.yaml`

This Service controls how the coordinator is exposed inside the cluster.

It also owns optional JMX exporter and additional exposed ports, which is why
it matters for monitoring and debugging.

### `service-worker.yaml`

This is the worker-side Service template. Most users can leave it alone unless
worker exposure needs to change.

### `serviceaccount.yaml`

This file controls whether Trino pods get a dedicated service account or reuse
an existing one. It matters whenever pod identity or cluster permissions are in
scope.

### `secret.yaml`

This upstream file still matters because file-password and group database
secrets may be generated here when shared identity is not completely replacing
those paths.

### `networkpolicy.yaml`, `autoscaler.yaml`, `ingress.yaml`,
`configmap-jmx-exporter.yaml`, `servicemonitor-*.yaml`, `NOTES.txt`

These are mostly standard upstream operational files:

- `networkpolicy.yaml` controls network isolation
- `autoscaler.yaml` controls worker autoscaling
- `ingress.yaml` controls optional ingress exposure
- `configmap-jmx-exporter.yaml` and `servicemonitor-*.yaml` support metrics
- `NOTES.txt` prints basic connection instructions

They are usually not the first place to look for repo-specific behavior, but
they still affect the running system.

## Common Tasks

If you need to:

- change generated Trino catalogs: edit `_helpers.tpl` and
  `configmap-catalog.yaml`
- change file-based Trino rules: edit `_helpers.tpl` or
  `configmap-access-control-coordinator.yaml`
- change coordinator auth, OIDC, or Ranger plugin behavior: inspect
  `configmap-coordinator.yaml` and `deployment-coordinator.yaml` together
- change worker rollout or secret wiring: edit `deployment-worker.yaml`
- understand Helm test coverage: read `tests/_README.txt`

## Validation

After changing anything here, run:

```bash
./hack/render-contract.sh
./hack/template.sh
./hack/lint.sh
```

Use the rendered output to confirm:

- the expected catalog files exist
- coordinator auth mode matches the intended identity model
- Ranger plugin config appears only when it should
- workers still receive the internal shared secret and graceful-shutdown config

## Common Mistakes

- changing a vendored upstream file without first checking whether a documented
  local patch point already owns the behavior
- assuming `configmap-access-control-worker.yaml` controls normal worker
  authorization instead of graceful shutdown only
- forgetting that Trino may still be using generated file-based access control
  even when Ranger is enabled elsewhere in the platform
- refreshing the vendored chart without re-checking the local patch files

## When You Can Ignore This Folder

You can ignore this folder unless you are changing Trino internals, auth,
catalog generation, or rollout behavior.
