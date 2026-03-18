# Third-Party Notices

This chart package includes third-party Helm chart material under the
dependencies listed in `Chart.yaml`.

The `dlh-in-a-box` umbrella chart code is licensed under Apache-2.0, but the
embedded dependency charts keep their own upstream licenses.

## Included third-party chart materials

| Material | Version or scope | License | Notes |
| --- | --- | --- | --- |
| Trino Helm chart | `0.34.0` | Apache-2.0 | Vendored locally and packaged as a dependency. Upstream Apache-2.0 text is included at `charts/trino/LICENSE`. Files modified for `dlh-in-a-box` contain prominent change notices. |
| Prefect Helm charts | `prefect-server` and `prefect-worker` `2025.12.31221620` | Apache-2.0 | Packaged upstream chart archives. These archives bundle Bitnami `common`, `postgresql`, and `redis` subcharts. |
| Spark Operator Helm chart | `2.4.0` | Apache-2.0 | Packaged upstream chart archive. |
| Bitnami Helm charts | `minio 15.0.7`, `postgresql 14.3.3`, and bundled `common` and `redis` subcharts | Apache-2.0 | Packaged upstream chart archives. The umbrella chart includes the Apache-2.0 text in `LICENSE`. |
| DataHub Helm chart and bundled subcharts | `0.8.21` and its bundled DataHub subcharts | Apache-2.0 | Packaged upstream chart archive. Upstream notice text is reproduced at `third_party/datahub/NOTICE`. |
| `datahub-prerequisites` Helm chart and bundled dependency charts | `0.2.3` and the upstream prerequisite charts it redistributes | Mixed upstream licenses: primarily Apache-2.0, plus MIT for the bundled `gcloud-sqlproxy` chart | Packaged upstream chart archive so the umbrella release can deploy DataHub and its prerequisites together. The bundled MIT license text is reproduced at `third_party/gcloud-sqlproxy/LICENSE`. |
| Vault Helm chart | `0.32.0` | MPL-2.0 | Packaged upstream dependency material. The packaged dependency includes `charts/vault/LICENSE`. |
| Local Hive subchart | `hive 0.1.0` | Apache-2.0 | Local subchart source packaged into the umbrella chart and covered by the umbrella chart's Apache-2.0 license. |

## Upstream sources

- Trino: `https://github.com/trinodb/charts`
- Prefect: `https://github.com/PrefectHQ/prefect-helm`
- Spark Operator: `https://github.com/kubeflow/spark-operator`
- Bitnami charts: `https://github.com/bitnami/charts`
- DataHub: `https://github.com/acryldata/datahub-helm`
- DataHub prerequisites: `https://github.com/acryldata/datahub-helm/tree/master/charts/prerequisites`
- Rimusz charts: `https://github.com/rimusz/charts`
- Vault: `https://github.com/hashicorp/vault-helm`

## Public release note

This package redistributes Helm chart sources and templates, not the runtime
container images referenced by those charts. If you redistribute mirrored
images or additional binaries, review those artifacts separately.
