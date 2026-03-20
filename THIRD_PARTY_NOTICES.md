# Third-Party Notices

This repository redistributes third-party Helm chart material as part of the
`dlh-in-a-box` umbrella chart.

This file documents the chart dependencies intentionally redistributed in this
repository, the licenses identified for them, and the steps taken here to keep
the public repository and published chart package aligned with their upstream
license obligations.

This is an engineering-facing compliance record, not formal legal advice.

## Scope

- Included: vendored chart source committed in-tree, upstream chart archives
  committed under `charts/dlh-in-a-box/charts/`, and the files shipped inside
  the published umbrella chart package.
- Not included: container images pulled at deploy time, downstream datasets,
  downstream application code, or external SaaS terms.

## Redistributed dependencies

| Material | Version or scope | License | How it is redistributed here | Compliance handling in this repo |
| --- | --- | --- | --- | --- |
| Trino Helm chart | `0.34.0` | Apache-2.0 | Vendored source at `charts/dlh-in-a-box/charts/trino/` and packaged as a local subchart dependency | Upstream Apache-2.0 text is included at `charts/dlh-in-a-box/charts/trino/LICENSE`. Files modified locally for `dlh-in-a-box` carry prominent notices stating that they were changed. |
| Apache Superset Helm chart | `0.15.2` | Apache-2.0 | Redistributed as an upstream chart archive | No local source modifications. The chart bundles Bitnami PostgreSQL and Redis subcharts, which stay covered by the Bitnami Apache-2.0 notices already documented here. |
| Prefect Helm charts | `prefect-server` and `prefect-worker` `2025.12.31221620` | Apache-2.0 | Redistributed as upstream chart archives | No local source modifications. The packaged Prefect charts also bundle Bitnami subcharts noted below. |
| Spark Operator Helm chart | `2.4.0` | Apache-2.0 | Redistributed as an upstream chart archive | No local source modifications. |
| Bitnami Helm charts | `minio 15.0.7`, `postgresql 14.3.3`, and bundled `common` and `redis` subcharts shipped by Bitnami and Prefect packages | Apache-2.0 | Redistributed as upstream chart archives and embedded subcharts inside those archives | No local source modifications. The umbrella chart package includes an Apache-2.0 license copy at `charts/dlh-in-a-box/LICENSE`. |
| DataHub Helm chart and bundled subcharts | `0.8.21` plus bundled `datahub-gms`, `datahub-frontend`, `datahub-mae-consumer`, `datahub-mce-consumer`, `datahub-ingestion-cron`, and `acryl-datahub-actions` subcharts | Apache-2.0 | Redistributed as an upstream chart archive | The upstream `NOTICE` file is reproduced at `charts/dlh-in-a-box/third_party/datahub/NOTICE` because the Apache-2.0 redistribution terms require readable notice reproduction when a distributed work ships with a `NOTICE` file. |
| `datahub-prerequisites` Helm chart and bundled dependency charts | `0.2.3` plus bundled Elasticsearch, MySQL, PostgreSQL, Kafka, Neo4j, OpenSearch, Confluent Platform, and `gcloud-sqlproxy` charts as shipped by the upstream dependency | Mixed upstream licenses: primarily Apache-2.0, plus MIT for the bundled `gcloud-sqlproxy` chart | Redistributed as an upstream chart archive | Included so `dlh-in-a-box` can deploy a self-contained DataHub baseline when `datahub.enabled=true`. The bundled MIT license text for `gcloud-sqlproxy` is reproduced at `charts/dlh-in-a-box/third_party/gcloud-sqlproxy/LICENSE`. |
| Vault Helm chart | `0.32.0` | MPL-2.0 | Redistributed as upstream dependency material in the repository and packaged chart | No local source modifications. The upstream dependency material carries `vault/LICENSE`; this repository also documents the upstream source and license below. |
| Local Hive subchart | `0.1.0` | Apache-2.0 | Local source under `charts/dlh-in-a-box/charts/hive/` and packaged as a local subchart dependency | Covered by this repository's Apache-2.0 license. |

## Upstream license sources reviewed

- Trino Helm charts: `https://github.com/trinodb/charts`
- Trino license: `https://github.com/trinodb/charts/blob/main/LICENSE`
- Apache Superset Helm chart: `https://github.com/apache/superset/tree/master/helm/superset`
- Prefect Helm charts: `https://github.com/PrefectHQ/prefect-helm`
- Prefect license: `https://github.com/PrefectHQ/prefect-helm/blob/main/LICENSE`
- Spark Operator Helm chart: `https://github.com/kubeflow/spark-operator`
- Spark Operator license: `https://github.com/kubeflow/spark-operator/blob/master/LICENSE`
- DataHub Helm charts: `https://github.com/acryldata/datahub-helm`
- DataHub license: `https://github.com/acryldata/datahub-helm/blob/master/LICENSE`
- DataHub notice: `https://github.com/acryldata/datahub-helm/blob/master/NOTICE`
- DataHub prerequisites chart: `https://github.com/acryldata/datahub-helm/tree/master/charts/prerequisites`
- Rimusz charts license for bundled `gcloud-sqlproxy`: `https://github.com/rimusz/charts/blob/master/LICENSE`
- Vault Helm chart: `https://github.com/hashicorp/vault-helm`
- Vault license: `https://github.com/hashicorp/vault-helm/blob/main/LICENSE`
- Bitnami charts: `https://github.com/bitnami/charts`
- Bitnami repository license page: `https://github.com/bitnami/charts/blob/main/LICENSE.md`

## Release checklist

Before publishing a new chart version:

1. Run `./hack/helm-dependency-update.sh` so local packaged dependencies match
   the current source tree.
2. Run `./hack/license-check.sh` to verify required notice files and local
   modification markers are still present.
3. Run `./hack/lint.sh` and package the chart.
4. If any dependency version changes, re-check whether the upstream license or
   `NOTICE` file changed before release.

## Important caveat

This repository and its OCI package redistribute Helm chart source and chart
archives. They do not themselves redistribute most of the application source
code or container images referenced by those charts. If you later mirror images
or ship a fuller binary distribution, do a separate license review for those
artifacts.
