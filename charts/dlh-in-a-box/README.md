# dlh-in-a-box Helm Chart

`dlh-in-a-box` is an umbrella Helm chart for deploying a modular lakehouse
control plane on Kubernetes. It packages upstream services where possible and
keeps local templates deliberately narrow: catalog generation, access-control
generation, Hive metastore wiring, and release-level compatibility glue.

## Chart architecture

```mermaid
flowchart LR
  Values[Helm values] --> Umbrella[dlh-in-a-box umbrella chart]
  Umbrella --> LocalGlue[Local templates and helpers]
  Umbrella --> Dependencies[Dependency charts]

  LocalGlue --> Catalogs[Trino catalogs and ACLs]
  LocalGlue --> HiveBootstrap[Hive metastore bootstrap]
  LocalGlue --> DataHubCompat[DataHub compatibility services]

  Dependencies --> Runtime[Kubernetes workloads]
  Catalogs --> Runtime
  HiveBootstrap --> Runtime
  DataHubCompat --> Runtime
```

## What this chart includes

| Component | Purpose | Source |
| --- | --- | --- |
| Trino | Query engine for lakehouse data access | Vendored upstream chart with local patches |
| Prefect Server | API and UI for orchestration | Upstream chart |
| Prefect Workers | Flow execution workers | Upstream chart |
| Spark Operator | Spark workload controller | Upstream chart |
| Hive Metastore | Per-catalog metadata service | Local subchart |
| Vault | Secret-management platform integration point | Upstream chart |
| MinIO | Optional self-contained S3-compatible object store | Upstream chart |
| DataHub | Optional metadata governance layer | Upstream chart |
| PostgreSQL | Hive metastore backing database | Upstream chart |

## Quick start

If you are evaluating the chart for the first time, pair this guide with
[../../docs/quickstart.md](../../docs/quickstart.md) for a shorter path from
inspection to installation.

Install directly from GHCR:

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

Stable releases are published from tags like `v0.2.0`. Pushes to `main`
publish uniquely versioned prereleases so downstream repositories can test the
latest chart state without waiting for a formal release.

## First-run checklist

```mermaid
flowchart TD
  Start[New consumer]
  Start --> Inspect[helm show chart or helm show readme]
  Inspect --> Pick[Choose an example overlay or consumer values]
  Pick --> Install[helm install or dependency build]
  Install --> Verify[Inspect workloads and service endpoints]
```

Recommended first steps:

1. Inspect the published package with `helm show chart` and `helm show readme`.
2. Decide whether you are validating locally or consuming from another repo.
3. Start from one of the example overlays instead of building values from scratch.
4. Verify package permissions in GHCR before troubleshooting Helm.

## Key values surface

| Top-level values key | Responsibility | Notes |
| --- | --- | --- |
| `global.storage` | Object-store endpoint, bucket, and path-style settings | Used by local composition logic and downstream services |
| `global.dataCatalogs` | Catalog definitions and authorized users | Drives generated Trino and Hive resources |
| `trino` | Upstream Trino settings | Includes locally generated catalog and access-control resources |
| `prefect` | Feature toggles for Prefect server and workers | Simple umbrella enablement surface |
| `prefectServer` | Direct pass-through to upstream Prefect Server chart | Includes PostgreSQL settings |
| `prefectWorker` | Direct pass-through to upstream Prefect Worker chart | Includes worker config and API connection |
| `sparkOperator` | Upstream Spark Operator settings | Feature toggle plus pass-through |
| `minio` | Upstream MinIO settings | Usually enabled for local deployments only |
| `datahub` | Upstream DataHub settings | Optional metadata layer |
| `datahubPrerequisites` | Upstream prerequisites chart values | Used only when DataHub is enabled |
| `hive` | Local metastore image, database, S3, and ingress settings | Powers one metastore per catalog |
| `vault` | Upstream Vault settings | Enabled by default |
| `postgresql` | Upstream PostgreSQL settings for Hive | Used when Hive is enabled |

## Deployment patterns

```mermaid
flowchart TD
  Start[Choose deployment mode]
  Start --> Local[Local validation]
  Start --> Shared[Shared cluster]
  Start --> Prod[Production baseline]

  Local --> LocalValues[examples/values-local.yaml]
  Local --> LocalLayers[examples/values-local-layers.yaml]
  Shared --> DevValues[examples/values-dev.yaml]
  Shared --> ExternalS3[examples/values-external-s3.yaml]
  Prod --> ProdValues[examples/values-prod.yaml]
  Prod --> ProdLayers[examples/values-prod-layers.yaml]
```

See [../../examples/README.md](../../examples/README.md) for the overlay
catalog and selection guidance.

## Consuming from another repository

For repositories in the same GitHub organization:

1. make sure the package `ghcr.io/sanger-pathogens/charts/dlh-in-a-box` exists
2. if package access is not inherited automatically, add the consumer
   repository under `Manage Actions access`
3. grant that repository `Read` access

In the consumer chart:

```yaml
dependencies:
  - name: dlh-in-a-box
    version: 0.2.0
    repository: oci://ghcr.io/sanger-pathogens/charts
```

In the consumer workflow:

```yaml
permissions:
  contents: read
  packages: read

steps:
  - uses: actions/checkout@v4
  - uses: azure/setup-helm@v4
  - name: Log in to GHCR
    run: |
      printf '%s' "${{ secrets.GITHUB_TOKEN }}" | \
        helm registry login ghcr.io -u "${{ github.actor }}" --password-stdin
  - name: Build chart dependencies
    run: helm dependency build
```

For prerelease integration builds, use the published
`-main.<run>.<attempt>.<sha>` version instead of a stable tag.

## Directory guides

| Path | Guide | Purpose |
| --- | --- | --- |
| `charts/` | [charts/README.md](../README.md) | Chart source tree overview |
| `charts/dlh-in-a-box/charts/` | [charts/dlh-in-a-box/charts/README.md](charts/README.md) | Local and vendored subchart inventory |
| `charts/dlh-in-a-box/charts/hive/` | [charts/dlh-in-a-box/charts/hive/README.md](charts/hive/README.md) | Hive subchart handover guide |
| `charts/dlh-in-a-box/charts/trino/` | [charts/dlh-in-a-box/charts/trino/README.md](charts/trino/README.md) | Vendored upstream Trino chart documentation |
| `charts/dlh-in-a-box/templates/` | [charts/dlh-in-a-box/templates/_README.txt](templates/_README.txt) | Umbrella-only glue templates |
| `charts/dlh-in-a-box/third_party/` | [charts/dlh-in-a-box/third_party/README.md](third_party/README.md) | Bundled notice material and provenance |

## Operational expectations

- do not commit real secrets to tracked values files
- treat example values as scaffolding rather than production-ready secret handling
- pin and review dependency changes deliberately
- treat `Chart.lock` as a release input, not generated noise
- use the maintainer scripts under `hack/` for repeatable validation

## Third-party licensing

This chart package redistributes upstream Helm charts under their own licenses.
See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the dependency
inventory and bundled notice material that ships with the package.

## License

Apache-2.0 applies to the umbrella chart itself. Third-party dependency notices
are documented in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
