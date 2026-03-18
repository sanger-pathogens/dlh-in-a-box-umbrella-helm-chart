# dlh-in-a-box Helm Chart

`dlh-in-a-box` is an umbrella Helm chart for deploying a modular lakehouse control plane on Kubernetes.

The chart packages upstream services where possible and keeps local templates limited to the composition logic that ties those services together: catalog generation, metastore wiring, and release-level integration.

## Included platform components

- Trino for interactive SQL
- Prefect Server and Prefect Workers for orchestration
- Spark Operator for Spark workload control
- Hive Metastore for table metadata
- Vault for secrets workflows
- MinIO for local or self-contained S3-compatible storage
- DataHub as an optional metadata/governance extension

## What this chart is designed for

Use this chart when you want:

- one Helm release to stand up a coherent lakehouse control plane
- a reusable OCI-packaged platform dependency for other repositories
- upstream-managed subcomponents with minimal local maintenance burden
- a validated local kind deployment path for development and testing

## Quick start

Install directly from OCI:

```bash
helm install dlh \
  oci://ghcr.io/sanger-pathogens/charts/dlh-in-a-box \
  --version <chart-version> \
  -n data-lakehouse \
  --create-namespace \
  -f my-values.yaml
```

Validate locally from source:

```bash
./hack/helm-dependency-update.sh
./hack/lint.sh
helm upgrade --install dlh charts/dlh-in-a-box \
  -n data-lakehouse-local \
  --create-namespace \
  -f examples/values-local.yaml
```

## Architectural summary

The chart is structured around a few clear responsibilities:

- Trino is the query front door.
- Hive Metastore supplies table metadata for Trino and Spark-compatible engines.
- Object storage is the durable data layer, using external S3-compatible storage by default or MinIO for self-contained deployments.
- Prefect coordinates flow execution and operational automation.
- Spark Operator manages Spark jobs submitted into the cluster.
- Vault provides an optional but first-class secrets platform.

## Key values surface

The chart keeps its public API focused around a small number of top-level sections:

- `global.storage`: object storage endpoint and bucket configuration
- `global.dataCatalogs`: catalog definitions and access rules
- `prefect`: component enablement flags
- `prefectServer` and `prefectWorker`: direct pass-throughs to upstream Prefect charts
- `trino`, `minio`, `sparkOperator`, `vault`, `datahub`: upstream component values
- `hive`: metastore, schema initialization, database, and S3 wiring
- `postgresql`: PostgreSQL settings used when Hive is enabled

## Operational expectations

- do not commit real secrets to tracked values files
- treat example values as scaffolding, not final production configuration
- pin and review dependency changes deliberately
- use `Chart.lock` as part of release review
- publish the packaged chart as an OCI artifact for downstream consumption

## Support material

- root architecture and repo guide: repository `README.md`
- example overlays: `examples/`
- helper scripts: `hack/`

## Third-party licensing

This chart package redistributes upstream Helm charts under their own licenses.
See `THIRD_PARTY_NOTICES.md` for the dependency inventory and bundled notice
material carried with the package.

## License

Apache-2.0 for the umbrella chart itself. Third-party dependency notices are in
`THIRD_PARTY_NOTICES.md`.
