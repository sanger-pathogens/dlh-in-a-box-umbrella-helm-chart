# dlh-in-a-box-umbrella-helm-chart

A true umbrella Helm chart for deploying an open-source data lakehouse platform on Kubernetes.

## Overview

This repository packages platform infrastructure components as upstream dependencies wherever practical, with minimal local templates for cross-component integration.

It is designed to be installable as a standalone umbrella chart and consumable as an OCI dependency from other repositories. It does not include pipeline code, Spark application code, or business logic.

## Usage

You can consume the chart in two ways.

Direct install from the published OCI artifact:

```bash
helm install dlh \
  oci://registry-1.docker.io/cv4551/dlh-in-a-box \
  --version 0.1.0 \
  -n data-lakehouse-local \
  --create-namespace \
  -f my-values.yaml
```

As a dependency from another repository:

1. Add it to your `Chart.yaml`:
   ```yaml
   dependencies:
     - name: dlh-in-a-box
       version: 0.1.0
       repository: oci://registry-1.docker.io/cv4551
       condition: dlh-in-a-box.enabled
   ```
2. Run `helm dependency build`.
3. Configure values in your `values.yaml` by merging with the provided examples from this repository.

For local development from this repository:
```bash
./hack/helm-dependency-update.sh
./hack/lint.sh
helm upgrade --install dlh charts/dlh-in-a-box \
  -n data-lakehouse-local \
  --create-namespace \
  -f examples/values-local.yaml
```

## Components

The umbrella chart coordinates the following components:

- Trino (default: enabled)
- Prefect Server (default: enabled)
- Prefect Workers (default: enabled)
- Spark Operator (default: enabled)
- Vault (default: enabled)
- MinIO (default: disabled)
- DataHub (default: disabled)
- Hive Metastore (default: disabled; local implementation with multi-schema support)

See [docs/components.md](docs/components.md) for details.

## Architecture

- The chart in `charts/dlh-in-a-box` defines upstream dependencies in `Chart.yaml`.
- Local templates are limited to:
  - storage secret normalization (`storage-config-secret.yaml`)
  - Prefect worker runtime config helper (`prefect-worker-config.yaml`)
  - standard Helm helper and notes templates
- Every major component can be enabled/disabled independently through values.

See [docs/architecture.md](docs/architecture.md).

## Configuration

### Data Catalogs

Configure data catalogs in `global.dataCatalogs` to define schemas and their types:

```yaml
global:
  dataCatalogs:
    bronze:
      type: deltaLake  # or hive
      authorizedUsers:
        read: ["user1", "analyst"]
        write: ["admin", "etl"]
    geospatial:
      type: hive
      authorizedUsers:
        read: ["user1"]
        write: ["admin"]
```

When `hive.enabled: true`, this will create metastore instances for each catalog and configure the Trino catalog config and access control rules to match.

### Storage

Default mode uses external S3-compatible storage. Optional in-cluster MinIO can be enabled.

- `global.storage.backend: externalS3` (default)
- `global.storage.backend: minio` (when MinIO is enabled)

See [docs/storage.md](docs/storage.md).

### Databases

Components deploy their own databases where possible:
- Prefect: PostgreSQL (enabled via `prefectServer.postgresql.enabled`)
- DataHub: MySQL (enabled via `datahubUpstream.mysql.enabled`)
- Hive: PostgreSQL (deployed when `hive.enabled`)

## Secrets management

Vault is included as a central secrets management component and can be disabled if an external Vault is used.

No secrets should be committed to Git. Use existing Kubernetes secrets and/or Vault-managed workflows.

See [docs/secrets.md](docs/secrets.md).

## Quick start (for testing only)

For local testing and development:

```bash
./hack/helm-dependency-update.sh
./hack/lint.sh
helm upgrade --install dlh charts/dlh-in-a-box \
  -n data-lakehouse-local \
  --create-namespace \
  -f examples/values-local.yaml
```

## Example configurations

- Development baseline: `examples/values-dev.yaml`
- Local kind profile: `examples/values-local.yaml`
- Production baseline: `examples/values-prod.yaml`
- External S3-focused config: `examples/values-external-s3.yaml`
- MinIO-enabled config: `examples/values-minio.yaml`

## Development notes

- Keep local templates minimal and integration-focused.
- Prefer upstream chart configuration over custom templating.
- Validate values with `values.schema.json`.
- Use helper scripts under `hack/` for repeatable local checks.
- OCI publication is automated via GitHub Actions in `.github/workflows/helm-publish.yaml`.

## Out of scope

- Data pipelines or orchestrated flows
- Spark applications or custom runtime images
- Environment-specific secrets in Git
- Complex custom reimplementation of upstream services

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE).
