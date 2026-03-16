# dlh-in-a-box-umbrella-helm-chart

A true umbrella Helm chart for deploying a modular, open-source data lakehouse platform on Kubernetes.

## Overview

This repository packages platform infrastructure components as upstream Helm chart dependencies wherever practical, with minimal local templates for cross-component integration.

It is intentionally **not** a monolithic custom chart and does not include pipeline code, Spark application code, or business logic.

## Components

The umbrella chart coordinates the following components:

- Trino (default: enabled)
- Prefect Server (default: enabled)
- Prefect Workers (default: enabled)
- Spark Operator (default: enabled)
- Vault (default: enabled)
- MinIO (default: disabled)
- DataHub (default: disabled)
- Hive Metastore (default: disabled; placeholder integration scaffold)

See [docs/components.md](docs/components.md) for details.

## Architecture

- The chart in `charts/dlh-in-a-box` defines upstream dependencies in `Chart.yaml`.
- Local templates are limited to:
  - storage secret normalization (`storage-config-secret.yaml`)
  - Prefect worker runtime config helper (`prefect-worker-config.yaml`)
  - standard Helm helper and notes templates
- Every major component can be enabled/disabled independently through values.

See [docs/architecture.md](docs/architecture.md).

## Storage model

Default mode uses external S3-compatible storage. Optional in-cluster MinIO can be enabled.

- `global.storage.backend: externalS3` (default)
- `global.storage.backend: minio` (when MinIO is enabled)

See [docs/storage.md](docs/storage.md).

## Secrets management

Vault is included as a central secrets management component and can be disabled if an external Vault is used.

No secrets should be committed to Git. Use existing Kubernetes secrets and/or Vault-managed workflows.

See [docs/secrets.md](docs/secrets.md).

## Quick start

```bash
./hack/helm-dependency-update.sh
./hack/lint.sh
helm install dlh charts/dlh-in-a-box -f examples/values-dev.yaml
```

## Example configurations

- Development baseline: `examples/values-dev.yaml`
- Production baseline: `examples/values-prod.yaml`
- External S3-focused config: `examples/values-external-s3.yaml`
- MinIO-enabled config: `examples/values-minio.yaml`

## Development notes

- Keep local templates minimal and integration-focused.
- Prefer upstream chart configuration over custom templating.
- Validate values with `values.schema.json`.
- Use helper scripts under `hack/` for repeatable local checks.

## Out of scope

- Data pipelines or orchestrated flows
- Spark applications or custom runtime images
- Environment-specific secrets in Git
- Complex custom reimplementation of upstream services

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE).
