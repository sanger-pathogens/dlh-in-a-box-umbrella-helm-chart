# Components

| Component | Purpose | Default | Delivery model | Notes |
|---|---|---|---|---|
| Trino | SQL query engine | Enabled | Upstream dependency | Configurable for external S3 or MinIO storage. |
| Prefect Server | Workflow orchestration API/UI | Enabled | Upstream dependency | Core orchestration control plane. |
| Prefect Workers | Flow execution workers | Enabled | Upstream dependency + light local config map | Worker pool/queue/replicas are modeled as first-class values. |
| Spark Operator | Spark workload orchestration controller | Enabled | Upstream dependency | No Spark jobs are included in this repo. |
| MinIO | In-cluster S3-compatible object storage | Disabled | Upstream dependency | Optional when external S3 is unavailable. |
| DataHub | Metadata catalog and governance platform | Disabled | Upstream dependency | Optional to keep default footprint lighter. |
| Hive Metastore | Table metadata service | Disabled | Placeholder local scaffold | Deliberately conservative until a concrete upstream/external selection is finalized. |
| Vault | Secrets management | Enabled | Upstream dependency | Central secrets component; can be disabled if external Vault is used. |
