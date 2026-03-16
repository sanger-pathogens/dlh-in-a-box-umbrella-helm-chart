# Architecture

## Umbrella chart approach

`charts/dlh-in-a-box` is a real umbrella Helm chart that composes multiple upstream components by dependency references in `Chart.yaml`.

The chart keeps local logic intentionally small and focused on cross-component composition:

- shared naming/labels helpers
- normalized storage secret pattern
- lightweight Prefect worker configuration surface

## High-level component model

The platform is modeled as independently toggleable components:

- Core query and compute control plane: Trino, Spark Operator
- Orchestration: Prefect server + Prefect workers
- Metadata and governance (optional): DataHub
- Object storage layer: external S3-compatible storage by default, optional MinIO
- Secrets management: Vault
- Hive Metastore: placeholder integration surface for future upstream/external metastore selection

## Intended usage

- Use `values.yaml` for defaults.
- Use environment overlays (`examples/` and your own overlays) for environment-specific customization.
- Keep secrets external to Git.
- Run in GitOps/CI by templating and linting the umbrella chart with per-environment values files.
