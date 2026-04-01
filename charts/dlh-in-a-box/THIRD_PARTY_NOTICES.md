# Third-Party Notices

This chart package includes third-party Helm chart material under the
dependencies listed in `Chart.yaml`.

The `dlh-in-a-box` umbrella chart code is licensed under Apache-2.0, but the
embedded dependency charts keep their own upstream licenses.

## Included third-party chart materials

| Material | Version or scope | License | Notes |
| --- | --- | --- | --- |
| Trino Helm chart | `0.34.0` | Apache-2.0 | Vendored locally and packaged as a dependency. Upstream Apache-2.0 text is included at `charts/trino/LICENSE`. Files modified for `dlh-in-a-box` contain prominent change notices. |
| Apache Superset Helm chart | `0.15.2` | Apache-2.0 | Packaged upstream chart archive. The chart bundles Bitnami PostgreSQL and Redis subcharts that stay covered by the Bitnami Apache-2.0 notices already documented here. |
| Prefect Helm charts | `prefect-server` and `prefect-worker` `2025.12.31221620` | Apache-2.0 | Packaged upstream chart archives. These archives bundle Bitnami `common`, `postgresql`, and `redis` subcharts. |
| oauth2-proxy Helm chart | `10.1.4` | MIT | Packaged upstream chart archive. Used to place self-hosted Prefect behind OIDC authentication in shared environments. The reproduced MIT license text is included at `third_party/oauth2-proxy/LICENSE`. |
| Bitnami keycloak Helm chart | `25.2.0` | Apache-2.0 | Packaged upstream Bitnami chart archive. Used for the default platform OIDC provider pattern. |
| Spark Operator Helm chart | `2.4.0` | Apache-2.0 | Packaged upstream chart archive. |
| Bitnami Helm charts | `minio 15.0.7`, `postgresql 14.3.3`, and bundled `common` and `redis` subcharts | Apache-2.0 | Packaged upstream chart archives. The umbrella chart includes the Apache-2.0 text in `LICENSE`. |
| DataHub Helm chart and bundled subcharts | `0.8.21` and its bundled DataHub subcharts | Apache-2.0 | Packaged upstream chart archive. Upstream notice text is reproduced at `third_party/datahub/NOTICE`. |
| `datahub-prerequisites` Helm chart and bundled dependency charts | `0.2.3` and the upstream prerequisite charts it redistributes | Mixed upstream licenses: primarily Apache-2.0, plus MIT for the bundled `gcloud-sqlproxy` chart | Packaged upstream chart archive so the umbrella release can deploy DataHub and its prerequisites together. The bundled MIT license text is reproduced at `third_party/gcloud-sqlproxy/LICENSE`. |
| Vault Helm chart | `0.32.0` | MPL-2.0 | Packaged upstream dependency material. The packaged dependency includes `charts/vault/LICENSE`. |
| Local Hive subchart | `hive 0.1.0` | Apache-2.0 | Local subchart source packaged into the umbrella chart and covered by the umbrella chart's Apache-2.0 license. |

## Upstream sources

- Trino: `https://github.com/trinodb/charts`
- Apache Superset: `https://github.com/apache/superset/tree/master/helm/superset`
- Prefect: `https://github.com/PrefectHQ/prefect-helm`
- oauth2-proxy: `https://github.com/oauth2-proxy/manifests`
- Keycloak: `https://github.com/bitnami/charts/tree/main/bitnami/keycloak`
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
