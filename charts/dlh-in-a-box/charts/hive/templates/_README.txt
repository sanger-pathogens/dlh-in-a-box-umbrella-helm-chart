# Hive Templates

This folder contains the render logic for the local Hive subchart.

Every file here is repo-owned. There is no upstream template set hiding behind
these files.

## Who Should Read This

| Reader | Why this guide matters |
| --- | --- |
| contributor | to know which template creates config, secrets, schema-init, and metastore runtime objects |
| operator | to understand how catalog count turns into rendered resources |

## Template Flow

```mermaid
flowchart TD
  subgraph Inputs["Template inputs"]
    Values[hive values]
    Catalogs[global dataCatalogs]
    Secrets[postgres and s3 inputs]
  end

  subgraph Templates["Hive templates"]
    Helpers[helpers]
    Config[config secret]
    InitConfig[init config]
    InitSchema[schema init job]
    Metastore[metastore runtime]
    PgSecret[postgres secret]
    S3Secret[s3 secret]
  end

  subgraph Output["Rendered resources"]
    Support[configmaps and secrets]
    Job[optional schema job]
    Runtime[services deployments ingress]
  end

  Values --> Helpers
  Catalogs --> Helpers
  Values --> Config
  Catalogs --> Config
  Values --> InitConfig
  Values --> InitSchema
  Values --> Metastore
  Secrets --> PgSecret
  Secrets --> S3Secret
  Helpers --> Config
  Helpers --> Metastore
  Config --> Support
  InitConfig --> Support
  PgSecret --> Support
  S3Secret --> Support
  InitSchema --> Job
  Support --> Runtime
  Metastore --> Runtime
```

## What Lives In This Folder

| File | Ownership | What it is for |
| --- | --- | --- |
| `_helpers.tpl` | repo-owned | naming and helper logic such as catalog-safe names and secret resolution |
| `configmap.yaml` | repo-owned | renders the per-catalog metastore configuration secret |
| `init-config.yaml` | repo-owned | renders the small ConfigMap with database host and port for init steps |
| `init-schema-job.yaml` | repo-owned | renders a per-catalog Job that creates or upgrades the metastore schema |
| `metastore.yaml` | repo-owned | renders the main Service, Deployment, and optional Ingress per catalog |
| `postgres-secret.yaml` | repo-owned | creates a PostgreSQL secret only when one is not supplied |
| `s3-secret.yaml` | repo-owned | creates an S3 credential secret only when one is not supplied |

## File-By-File Behavior

### `_helpers.tpl`

This file keeps the rest of the templates readable.

It holds helper functions for:

- subchart naming
- catalog name sanitization for Kubernetes object names
- resolving the effective PostgreSQL host
- resolving which PostgreSQL and S3 secret names to mount
- computing checksums used by rollout annotations
- shared JDBC driver init container, volume, and volumeMount fragments

The JDBC helper templates (`hive.downloadJdbcInitContainer`,
`hive.jdbcDriverVolume`, `hive.jdbcDriverVolumeMount`) are used by
`metastore.yaml`. If the download source or mount path needs changing, this
file is the single place to change it.

`hive.waitForPostgresInitContainer` is used by both `metastore.yaml` and
`init-schema-job.yaml` as the first init container, polling `pg_isready` before
any schema work runs.

When multiple templates need the same naming or secret-selection logic, the
change belongs here.

### `configmap.yaml`

Despite the filename, this template renders a `Secret`, not a `ConfigMap`.

That is deliberate because the generated `core-site.xml` and
`metastore-site.xml` include storage and database credentials.

For each catalog, it creates one secret containing:

- `core-site.xml` with S3 endpoint, path-style flag, and credentials
- `metastore-site.xml` with JDBC connection information and warehouse location

This file is the main bridge from shared catalog and storage values into usable
Hive configuration.

### `init-config.yaml`

This template renders one small ConfigMap containing:

- `POSTGRES_HOST`
- `POSTGRES_PORT`

The metastore Deployment init containers consume this ConfigMap so the host and
port logic lives in one place.

### `init-schema-job.yaml`

This template renders one Job per catalog when `schemainit.job.enabled=true`.

The Job is a regular Kubernetes resource with no Helm hooks. It runs alongside
the metastore Deployment and completes once the schema is created or upgraded.

Each Job runs init containers in order:

1. `wait-for-postgres` — polls `pg_isready` until PostgreSQL accepts connections
2. `download-jdbc` — fetches the PostgreSQL JDBC driver
3. `create-db` (optional, when `postgres.createDatabase=true`) — creates the
   catalog database if it does not exist

The main container then runs `schematool -upgradeSchema`, falling back to
`schematool -initSchema` if no schema exists yet.

The Job name includes the Hive image tag so that a chart upgrade that bumps the
image version creates a new Job, which triggers a schema upgrade automatically.

### `metastore.yaml`

This is the main runtime template in the subchart.

For each catalog, it renders:

- a ClusterIP Service on port `9083`
- a Deployment with init containers that act as readiness gates
- an optional Ingress when enabled

Important details owned here:

- checksum annotations for config and secret changes
- a `wait-for-postgres` init container that polls `pg_isready` until PostgreSQL
  is accepting connections
- a `download-jdbc` init container that fetches the PostgreSQL JDBC driver
- a `wait-for-schema` init container that loops on `schematool -info` until the
  schema exists and is at the expected version; this gates the metastore on the
  schema Job having completed
- environment and volume wiring for the Hive image, including the JDBC driver
  on `HADOOP_CLASSPATH`
- mounting the per-catalog metastore configuration secret
- per-catalog hostnames for optional ingress exposure

The metastore Deployment does not create or modify the schema. All schema work
happens in `init-schema-job.yaml`. On restart, `schematool -info` passes quickly
because the schema already exists.

If a metastore pod will not start, this is the first template to inspect.

### `postgres-secret.yaml`

This template creates a small PostgreSQL secret only when
`postgres.existingSecret` is empty.

That means there are two supported secret paths:

- inline username and password values generate a secret here
- an existing secret is supplied and this template renders nothing

Any change to secret key names or generation behavior should be made carefully
because the Deployment expects matching keys.

### `s3-secret.yaml`

This template works the same way as `postgres-secret.yaml`, but for object
storage credentials.

It creates a secret only when `s3.existingSecret` is not provided.

Because these values are mounted into Hive runtime config, changes here should
always be checked against `configmap.yaml` and `metastore.yaml`.

## Common Tasks

If you need to:

- change generated Hive XML: edit `configmap.yaml`
- change how PostgreSQL host and port are shared: edit `init-config.yaml`
- change schema init or upgrade behavior: edit `init-schema-job.yaml`
- change the metastore readiness gate (how long it waits for the schema): edit `metastore.yaml`
- change the JDBC driver URL or mount path: edit `_helpers.tpl`
- change pod startup, mounts, probes, or ingress: edit `metastore.yaml`
- change secret generation fallback: edit `postgres-secret.yaml` or
  `s3-secret.yaml`

## Validation

After changing these templates, run:

```bash
make verify
```

Check the rendered output for:

- one metastore secret per catalog
- one Service and Deployment per catalog
- the expected secret path, generated or existing
- correct warehouse and JDBC settings

## Common Mistakes

- forgetting that `configmap.yaml` intentionally renders a secret because it
  contains credentials
- editing the `download-jdbc` or `wait-for-postgres` init containers directly
  in `metastore.yaml` or `init-schema-job.yaml` without realizing they come from
  `_helpers.tpl`; always change the helper
- expecting the metastore to create or upgrade the schema on restart; it does
  not — the schema Job owns that
- disabling the schema Job (`schemainit.job.enabled=false`) without having an
  external mechanism to create the schema; the metastore will hang waiting
- testing with a catalog-free values file and concluding the template did
  nothing
- changing secret key names without checking how the Deployment consumes them

## When You Can Ignore This Folder

You can ignore this folder unless you are changing Hive runtime generation or
debugging how catalog definitions become metastore resources.
