# DLH-in-a-box IcePanel Model

This document defines a focused C4/IcePanel architecture model for the
`dlh-in-a-box` umbrella Helm chart. The model describes the chart as a reusable
deployment product and the generic data lakehouse runtime that it instantiates.
It intentionally excludes the Sanger development deployment, the icddr,b
production deployment, PaM/ICDDRB realm ownership, and project-specific pipeline
repositories, except where those assets appear as external consumers or
deployment context.

Use this model as a separate IcePanel domain or system view when the audience
needs to understand DLH-in-a-box independently of any single deployment.

The canonical IcePanel-as-code source for synchronization is
`docs/architecture/icepanel/models/dlh-in-a-box.json`. This Markdown document is
the publication-readable companion and source evidence narrative.

---

## Source Evidence

| Source | What it informs |
| --- | --- |
| `/Users/CV4/code/dlh-in-a-box-umbrella-helm-chart/charts/dlh-in-a-box/Chart.yaml` | Chart identity, dependency list, component names, repositories, and conditions. |
| `/Users/CV4/code/dlh-in-a-box-umbrella-helm-chart/charts/dlh-in-a-box/Chart.lock` | Resolved dependency versions and digests. |
| `/Users/CV4/code/dlh-in-a-box-umbrella-helm-chart/charts/dlh-in-a-box/values.yaml` | Default runtime shape and feature toggles. |
| `/Users/CV4/code/dlh-in-a-box-umbrella-helm-chart/charts/dlh-in-a-box/templates/` | First-party umbrella templates. |
| `/Users/CV4/code/dlh-in-a-box-umbrella-helm-chart/charts/dlh-in-a-box/charts/` | Packaged archives, local Hive subchart, and vendored Trino chart. |
| `/Users/CV4/code/dlh-in-a-box-umbrella-helm-chart/examples/` | Supported install profiles that turn optional runtime services on or off. |
| `/Users/CV4/code/dlh-in-a-box-umbrella-helm-chart/hack/` and `.github/workflows/` | Validation, smoke, dependency refresh, package, and publish automation. |

---

## Modelling Rules

| Rule | Guidance |
| --- | --- |
| Level 1 | Represent the chart product, platform operators, upstream dependency sources, consumer deployment repositories, target Kubernetes clusters, and users of the deployed platform. |
| Level 2 | Use one container diagram for the chart product and packaging pathway, and one for the generic runtime deployed by the chart. |
| Level 3 | Add component diagrams only beneath owned or reviewed Level 2 applications and stores, such as the chart source, local Hive subchart, vendored Trino chart, validation automation, and publish automation. |
| Groups | Use groups only as visual boundaries. Do not draw arrows to or from groups. |
| Environments | Keep Sanger OpenStack, icddr,b VMware, DNS, TLS, storage classes, and institution-specific settings out of this model unless shown as external deployment context. |
| DataHub | Model DataHub as optional per deployment. It may support discovery of available data products, but it is not yet the required data-mesh governance service. |

---

## Level 1 Context Diagram

### Objects

| ID | Name | IcePanel Type | Status | Description |
| --- | --- | --- | --- | --- |
| `DLH-L1-OPERATOR` | Platform Operator | `Actor` | Live | Administrator who prepares institutional configuration and manages the deployed Data Lakehouse instance. |
| `DLH-L1-USER` | Platform User | `Actor` | Live | Researcher, analyst, or data scientist using browser tools and governed data services. |
| `DLH-L1-CHART` | DLH-in-a-box Umbrella Helm Chart | `System` | Live | Reusable Umbrella Helm Chart that bundles open-source services into a research data lakehouse. |
| `DLH-L1-CONSUMER-REPO` | Consumer Deployment Repository | `System` | Live | Institution-specific repository recording the chart version and settings used for deployment. |
| `DLH-L1-UPSTREAM-DEPS` | Upstream Dependency Sources | `System` | Live | External open-source Helm charts and container images bundled, vendored, or referenced by the package. |
| `DLH-L1-RUNTIME` | Deployed DLH-in-a-box Runtime | `System` | Instance | Running DLH-in-a-box instance created from the chart and institutional configuration for lakehouse users. |
| `DLH-L1-TARGET-CLUSTER` | Target Kubernetes Cluster | `System` | Live | Institutional Kubernetes environment providing compute, networking, and storage for the runtime. |

### Relationships

| From | To | Label |
| --- | --- | --- |
| `DLH-L1-OPERATOR` | `DLH-L1-CONSUMER-REPO` | prepares institutional deployment configuration |
| `DLH-L1-CONSUMER-REPO` | `DLH-L1-CHART` | selects published Helm chart |
| `DLH-L1-CONSUMER-REPO` | `DLH-L1-RUNTIME` | provides deployment configuration |
| `DLH-L1-UPSTREAM-DEPS` | `DLH-L1-CHART` | provides packaged charts and images |
| `DLH-L1-CHART` | `DLH-L1-RUNTIME` | defines deployable lakehouse runtime |
| `DLH-L1-RUNTIME` | `DLH-L1-TARGET-CLUSTER` | runs on institutional Kubernetes infrastructure |
| `DLH-L1-USER` | `DLH-L1-RUNTIME` | uses analytical tools and governed data services |
| `DLH-L1-OPERATOR` | `DLH-L1-RUNTIME` | manages deployed Data Lakehouse instance |

### Layout

Place the chart product and consumer deployment repository on the left, the
deployed runtime instance in the centre, and the target Kubernetes cluster
behind or below the runtime. Place upstream dependency sources where they feed
the chart. Place users and operators around the deployed runtime, because the
runtime is the system they experience operationally.

### Figure Caption

Context diagram for DLH-in-a-box. The Umbrella Helm Chart is a reusable
Kubernetes package; institutional deployment repositories select a chart version
and provide local settings; the resulting runtime runs on institutional
Kubernetes infrastructure and exposes integrated lakehouse services to
researchers.

---

## Level 2 Container Diagram A: Chart Product And Packaging

This diagram describes the Helm chart repository as a reusable software
product. It should not include Sanger or icddr,b deployment-specific settings.

### Visual Groups

| Group | Contains | Notes |
| --- | --- | --- |
| Upstream Sources | External Helm chart sources and Hive image | Draw arrows from individual systems, not from this group. |
| Chart Source | Chart source, local subcharts, vendored chart, packaged archives | Owned by the upstream umbrella chart repository. |
| Install Profiles | Example configuration files | Profiles document supported deployment shapes; they are not themselves current deployments. |
| Automation | Validation automation and publish automation | Continuous integration and release scripts that verify and publish the chart. |
| Published Artifact | Published OCI chart package | Versioned artifact consumed by deployment repositories. |

### Internal Apps And Stores

| ID | Name | IcePanel Type | Technology | Path | Description |
| --- | --- | --- | --- | --- | --- |
| `DLH-C2-CHART-SOURCE` | Chart Source | `Store` | Helm chart source | `charts/dlh-in-a-box/` | Primary source tree for the umbrella Helm chart; defines chart metadata, default configuration, templates, and dependencies. |
| `DLH-C2-UPSTREAM-ARCHIVES` | Packaged Upstream Dependency Helm Charts | `Store` | `.tgz` Helm archives | `charts/dlh-in-a-box/charts/*.tgz` | Version-resolved Helm dependency archives bundled with the chart to make dependency resolution explicit and reproducible. |
| `DLH-C2-TRINO-VENDORED` | Vendored Trino Chart | `Store` | Helm chart source/archive | `charts/dlh-in-a-box/charts/trino/`; `charts/dlh-in-a-box/charts/trino-0.34.0.tgz` | Local copy of the upstream Trino chart adapted for DLH-in-a-box identity, storage, and access-control integration. |
| `DLH-C2-HIVE-SUBCHART` | Hive Metastore Local Subchart | `Store` | Helm subchart | `charts/dlh-in-a-box/charts/hive/`; `charts/dlh-in-a-box/charts/hive-0.1.0.tgz` | First-party Helm subchart that renders the optional Hive Metastore service used for SQL catalog metadata. |
| `DLH-C2-EXAMPLE-PROFILES` | Example Values Profiles | `Store` | YAML example configuration files | `examples/*.yaml` | Example configuration files that demonstrate and test supported installation modes, including local, development, production, shared identity, in-cluster MinIO, and external S3 configurations. |
| `DLH-C2-VALIDATION` | Chart Validation Automation | `App` | GitHub Actions / shell | `.github/workflows/helm-lint.yaml`; `.github/workflows/helm-smoke-install.yaml`; `hack/` | Automated checks that lint, render, smoke-install, and test the package against documented configuration rules before publication. |
| `DLH-C2-PUBLISH` | Chart Publish Automation | `App` | GitHub Actions / Helm | `.github/workflows/helm-publish.yaml`; `hack/package.sh` | Release automation that builds versioned Helm artifacts and publishes them for deployment repositories. |
| `DLH-C2-OCI-PACKAGE` | Published OCI Chart Package | `Store` | GHCR OCI Helm artifact | `oci://ghcr.io/sanger-pathogens/charts/dlh-in-a-box` | Versioned Helm chart artifact stored in the GHCR OCI registry and consumed by deployment repositories. |

### External Systems

| ID | Name | IcePanel Type | Technology | Description |
| --- | --- | --- | --- | --- |
| `DLH-X-SUPERSET-CHART` | Upstream Superset Helm Chart | `System` | Helm | Canonical upstream chart source from which the optional Superset dashboarding dependency is packaged. |
| `DLH-X-PREFECT-SERVER-CHART` | Upstream Prefect Server Helm Chart | `System` | Helm | Canonical upstream chart source for the Prefect orchestration server dependency. |
| `DLH-X-PREFECT-WORKER-CHART` | Upstream Prefect Worker Helm Chart | `System` | Helm | Canonical upstream chart source for the Prefect worker service that executes pipeline jobs. |
| `DLH-X-OAUTH2-PROXY-CHART` | Upstream oauth2-proxy Helm Chart | `System` | Helm | Canonical upstream chart source for browser authentication proxies that validate OIDC sessions before users reach protected applications. |
| `DLH-X-KEYCLOAK-CHART` | Upstream Keycloak Helm Chart | `System` | Helm | Canonical upstream chart source for Keycloak when the lakehouse deploys its own OIDC identity provider. |
| `DLH-X-SPARK-OPERATOR-CHART` | Upstream Spark Operator Helm Chart | `System` | Helm | Canonical upstream chart source for the Kubernetes operator that manages Spark applications. |
| `DLH-X-MINIO-CHART` | Upstream MinIO Helm Chart | `System` | Helm | Canonical upstream chart source for the optional in-cluster S3-compatible object store. |
| `DLH-X-DATAHUB-CHART` | Upstream DataHub Helm Chart | `System` | Helm | Canonical upstream chart source for optional metadata catalog and discovery services. |
| `DLH-X-DATAHUB-PREREQS-CHART` | Upstream DataHub Prerequisites Chart | `System` | Helm | Canonical upstream chart source for the persistence, messaging, and search services required by DataHub. |
| `DLH-X-VAULT-CHART` | Upstream Vault Helm Chart | `System` | Helm | Canonical upstream chart source for optional secret management included with the chart. |
| `DLH-X-JUPYTERHUB-CHART` | Upstream JupyterHub Helm Chart | `System` | Helm | Canonical upstream chart source for the optional multi-user notebook service. |
| `DLH-X-POSTGRESQL-CHART` | Upstream PostgreSQL Helm Chart | `System` | Helm | Canonical upstream chart source for relational stores used by several platform services. |
| `DLH-X-TRINO-CHART` | Upstream Trino Helm Chart | `System` | Helm | Canonical upstream Trino chart source from which the local Trino chart is derived. |
| `DLH-X-HIVE-IMAGE` | Hive Metastore Container Image | `System` | Docker image | Runtime container image referenced by the local Hive subchart to run the Hive Metastore service. |
| `DLH-X-CONSUMER-REPO` | Consumer Deployment Repository | `System` | Git repository | Institution-specific repository that selects a published chart version and deployment settings. |

### Relationships

| From | To | Label |
| --- | --- | --- |
| `DLH-X-SUPERSET-CHART` | `DLH-C2-UPSTREAM-ARCHIVES` | is packaged into |
| `DLH-X-PREFECT-SERVER-CHART` | `DLH-C2-UPSTREAM-ARCHIVES` | is packaged into |
| `DLH-X-PREFECT-WORKER-CHART` | `DLH-C2-UPSTREAM-ARCHIVES` | is packaged into |
| `DLH-X-OAUTH2-PROXY-CHART` | `DLH-C2-UPSTREAM-ARCHIVES` | is packaged into |
| `DLH-X-KEYCLOAK-CHART` | `DLH-C2-UPSTREAM-ARCHIVES` | is packaged into |
| `DLH-X-SPARK-OPERATOR-CHART` | `DLH-C2-UPSTREAM-ARCHIVES` | is packaged into |
| `DLH-X-MINIO-CHART` | `DLH-C2-UPSTREAM-ARCHIVES` | is packaged into |
| `DLH-X-DATAHUB-CHART` | `DLH-C2-UPSTREAM-ARCHIVES` | is packaged into |
| `DLH-X-DATAHUB-PREREQS-CHART` | `DLH-C2-UPSTREAM-ARCHIVES` | is packaged into |
| `DLH-X-VAULT-CHART` | `DLH-C2-UPSTREAM-ARCHIVES` | is packaged into |
| `DLH-X-JUPYTERHUB-CHART` | `DLH-C2-UPSTREAM-ARCHIVES` | is packaged into |
| `DLH-X-POSTGRESQL-CHART` | `DLH-C2-UPSTREAM-ARCHIVES` | is packaged into |
| `DLH-X-TRINO-CHART` | `DLH-C2-TRINO-VENDORED` | is adapted as local Trino chart |
| `DLH-X-HIVE-IMAGE` | `DLH-C2-HIVE-SUBCHART` | is referenced by |
| `DLH-C2-CHART-SOURCE` | `DLH-C2-UPSTREAM-ARCHIVES` | declares and contains |
| `DLH-C2-CHART-SOURCE` | `DLH-C2-TRINO-VENDORED` | declares and contains |
| `DLH-C2-CHART-SOURCE` | `DLH-C2-HIVE-SUBCHART` | declares and contains |
| `DLH-C2-VALIDATION` | `DLH-C2-CHART-SOURCE` | validates |
| `DLH-C2-VALIDATION` | `DLH-C2-EXAMPLE-PROFILES` | tests example configurations |
| `DLH-C2-PUBLISH` | `DLH-C2-CHART-SOURCE` | packages |
| `DLH-C2-PUBLISH` | `DLH-C2-OCI-PACKAGE` | publishes |
| `DLH-X-CONSUMER-REPO` | `DLH-C2-EXAMPLE-PROFILES` | uses example configurations from |
| `DLH-X-CONSUMER-REPO` | `DLH-C2-OCI-PACKAGE` | selects chart version from |

### Layout

Put individual upstream chart systems on the left. Put `Chart Source` in the
centre with the three dependency stores nearby. Put validation/publish
automation below the chart source. Put the published OCI chart package on the
right with consumer deployment repositories further right.

---

## Level 2 Container Diagram B: Runtime Deployed By The Chart

This diagram describes the generic lakehouse runtime that the chart can deploy.
It is not an icddr,b development or production deployment diagram; treat
environment-specific infrastructure as external infrastructure.

The default settings in upstream `values.yaml` are intentionally modular:
`trino`, `prefect`, `sparkOperator`, and `vault` are enabled by default, while
browser identity, Ranger governance, MinIO, Hive, Superset, JupyterHub,
CloudBeaver, and DataHub are turned on by install profiles or
institution-specific settings as needed.

### Visual Groups

| Group | Contains | Notes |
| --- | --- | --- |
| Browser Entry | Platform Home and browser-facing application endpoints | The ingress controller itself is usually cluster infrastructure. |
| Identity And Secrets | Keycloak, external OIDC integration, optional Vault, auth proxy instances | External secret delivery may be cluster infrastructure in some deployments. |
| Governance | Ranger | Optional governed Trino access. |
| Lakehouse Core | Trino, optional Hive Metastore, MinIO or external S3, and their stores | Primary analytical data plane. |
| Analysis Tools | Superset, JupyterHub, CloudBeaver | Human-facing analytics tools. |
| Orchestration And Compute | Prefect Server, Prefect Worker, Spark Operator | Pipeline orchestration and distributed job runtime. |
| Discovery | Optional DataHub service | Enabled per deployment. |
| Support Services And Stores | PostgreSQL, Redis, MySQL, Kafka, Elasticsearch | Place each service or store near the application that owns it where possible. |

### Deployed Apps And Stores

| ID | Name | IcePanel Type | Technology | Enabled By | Default | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `DLH-R-TRINO` | Trino | `App` | Trino coordinator + workers | `trino.enabled` | On | Distributed SQL query engine that provides the principal compute interface for querying and transforming governed lakehouse datasets. |
| `DLH-R-PREFECT-SERVER` | Prefect Server | `App` | Prefect | `prefect.enabled`; `prefect.server.enabled` | On | Orchestration service that stores flow definitions, schedules, run state, and exposes the operational API and UI for data workflows. |
| `DLH-R-PREFECT-DB` | Prefect Database | `Store` | PostgreSQL | `prefectServer.postgresql.enabled` | On | PostgreSQL store that persists Prefect orchestration metadata, including flow runs, schedules, and state transitions. |
| `DLH-R-PREFECT-WORKER` | Prefect Worker | `App` | Prefect Kubernetes worker | `prefect.enabled`; `prefect.workers.enabled` | On | Kubernetes-based execution worker that retrieves approved flow runs from Prefect Server and launches the corresponding pipeline jobs. |
| `DLH-R-SPARK-OPERATOR` | Spark Operator | `App` | Kubeflow Spark Operator | `sparkOperator.enabled` | On | Kubernetes operator that manages Spark applications submitted by pipeline jobs for distributed processing. |
| `DLH-R-VAULT` | Vault | `App` | HashiCorp Vault | `vault.enabled` | On | Optional secret-management service included with the chart; deployments may instead integrate with an external Vault or equivalent secret provider. |
| `DLH-R-PLATFORM-HOME` | Platform Home | `App` | nginx + API | `platformHome.enabled` | Off | Browser portal that presents authenticated launch links and health information for deployed platform services; the current implementation assumes bundled Keycloak. |
| `DLH-R-KEYCLOAK` | Keycloak | `App` | Keycloak | `keycloak.enabled`; `global.identity.provider.mode=bundledKeycloak` | Off | Optional in-chart OIDC identity provider that issues browser and service authentication tokens and supplies role or group claims. |
| `DLH-R-KEYCLOAK-DB` | Keycloak Database | `Store` | PostgreSQL | `keycloak.postgresql.enabled` | Conditional | PostgreSQL persistence layer for Keycloak realms, clients, users, sessions, and configuration when bundled Keycloak is enabled. |
| `DLH-R-AUTH-PROXIES` | Browser Auth Proxies | `App` | oauth2-proxy instances | application auth-proxy settings | Off | oauth2-proxy instances that enforce browser sign-in in front of selected applications, including Ranger, CloudBeaver, and Prefect. |
| `DLH-R-RANGER` | Ranger | `App` | Apache Ranger | `global.authorization.ranger.enabled` | Off | Optional policy administration service for governed SQL access, including roles, data masking, row filters, and audit. |
| `DLH-R-RANGER-DB` | Ranger Database | `Store` | PostgreSQL | Ranger PostgreSQL dependency/settings | Conditional | PostgreSQL store for Ranger policy definitions, users, roles, service metadata, and audit-related state. |
| `DLH-R-MINIO` | In-Cluster Object Store | `Store` | MinIO / S3 API | `minio.enabled`; `global.storage.backend=minio` | Off | Optional S3-compatible object store deployed inside the cluster when a deployment does not use an external object-storage service. |
| `DLH-R-HIVE` | Hive Metastore | `App` | Hive Metastore | `hive.enabled` | Off | Optional metastore service that records database, table, partition, and schema metadata used by Trino to interpret data in object storage. |
| `DLH-R-HIVE-DB` | Hive Database | `Store` | PostgreSQL | `hivePostgresql` dependency/settings | Conditional | PostgreSQL persistence layer for Hive Metastore catalog metadata. |
| `DLH-R-SUPERSET` | Superset | `App` | Apache Superset | `superset.enabled` | Off | Optional web application for business intelligence, dashboard development, and visual exploration of governed datasets through Trino. |
| `DLH-R-SUPERSET-DB` | Superset Database | `Store` | PostgreSQL | Superset chart settings | Conditional | Relational metadata store for Superset users, dashboards, charts, datasets, and application settings. |
| `DLH-R-SUPERSET-REDIS` | Superset Queue | `Store` | Redis | Superset chart settings | Conditional | Cache and asynchronous task queue used by Superset for responsive dashboard execution and background work. |
| `DLH-R-JUPYTERHUB` | JupyterHub | `App` | JupyterHub | `jupyterhub.enabled` | Off | Optional multi-user notebook service for code-oriented scientific analysis in authenticated, per-user compute environments. |
| `DLH-R-JUPYTER-PODS` | User Notebook Pods | `App` | Kubernetes pods | JupyterHub user server spawning | Conditional | Ephemeral Kubernetes pods spawned by JupyterHub to provide isolated notebook runtimes for individual users. |
| `DLH-R-CLOUDBEAVER` | CloudBeaver | `App` | CloudBeaver | `cloudbeaver.enabled` | Off | Optional browser-based SQL workbench that enables interactive exploration of Trino catalogs without local client installation. |
| `DLH-R-DATAHUB` | DataHub | `App` | DataHub | `datahub.enabled` | Off | Optional metadata catalog and discovery service for browsing data products, lineage, and platform assets. |
| `DLH-R-DATAHUB-MYSQL` | DataHub MySQL Database | `Store` | MySQL | `datahubPrerequisites.mysql.enabled` | Conditional | Relational database used by DataHub to persist metadata state and application records. |
| `DLH-R-DATAHUB-KAFKA` | DataHub Kafka | `Store` | Kafka | `datahubPrerequisites.kafka.enabled` | Conditional | Event-stream service used by DataHub to exchange metadata change events between services. |
| `DLH-R-DATAHUB-ELASTICSEARCH` | DataHub Search Index | `Store` | Elasticsearch | `datahubPrerequisites.elasticsearch.enabled` | Conditional | Search index used by DataHub to make metadata entities discoverable in the catalog interface. |

### External Runtime Context

| ID | Name | IcePanel Type | Description |
| --- | --- | --- | --- |
| `DLH-X-USERS` | Platform Users | `Actor` | Researchers, analysts, and authorized staff who access browser applications and governed data services. |
| `DLH-X-INGRESS-CONTROLLER` | Cluster Ingress Controller | `System` | Cluster-provided ingress layer that routes HTTPS requests to platform endpoints. |
| `DLH-X-OIDC` | External OIDC Provider | `System` | Institutional or external OIDC identity provider used when the deployment does not use bundled Keycloak. |
| `DLH-X-LDAP` | External LDAP / AD Directory | `System` | Enterprise directory that supplies users and groups to Keycloak when identity federation is configured. |
| `DLH-X-OBJECT-STORAGE` | External S3-Compatible Object Store | `System` | External object-storage service that contains lakehouse data objects when the deployment uses external S3-compatible storage. |
| `DLH-X-SECRET-SYNC` | External Secret Delivery | `System` | External mechanism that creates Kubernetes Secrets consumed by the release, such as Vault Secrets Operator. |
| `DLH-X-PIPELINE-CODE` | Reviewed Pipeline Code | `System` | Reviewed workflow definitions, dbt models, and runtime images that execute inside the lakehouse environment through Prefect or related tools. |
| `DLH-X-SOURCE-SYSTEMS` | Source Systems | `System` | Operational, surveillance, survey, public climate, and other upstream data systems from which pipelines extract source data. |

### Runtime Relationships

| From | To | Label |
| --- | --- | --- |
| `DLH-X-USERS` | `DLH-X-INGRESS-CONTROLLER` | access platform over HTTPS |
| `DLH-X-INGRESS-CONTROLLER` | `DLH-R-PLATFORM-HOME` | routes portal traffic |
| `DLH-X-INGRESS-CONTROLLER` | `DLH-R-AUTH-PROXIES` | routes protected application traffic |
| `DLH-X-INGRESS-CONTROLLER` | `DLH-R-VAULT` | routes Vault UI traffic when enabled |
| `DLH-R-PLATFORM-HOME` | `DLH-R-KEYCLOAK` | authenticates portal users with bundled Keycloak |
| `DLH-R-AUTH-PROXIES` | `DLH-R-KEYCLOAK` | validates sessions when bundled Keycloak is used |
| `DLH-R-AUTH-PROXIES` | `DLH-X-OIDC` | validates sessions when external OIDC is used |
| `DLH-R-TRINO` | `DLH-R-KEYCLOAK` | authenticates users when bundled Keycloak is used |
| `DLH-R-TRINO` | `DLH-X-OIDC` | authenticates users when external OIDC is used |
| `DLH-R-JUPYTERHUB` | `DLH-R-KEYCLOAK` | authenticates notebook users when bundled Keycloak is used |
| `DLH-R-JUPYTERHUB` | `DLH-X-OIDC` | authenticates notebook users when external OIDC is used |
| `DLH-R-SUPERSET` | `DLH-R-KEYCLOAK` | authenticates dashboard users when bundled Keycloak is used |
| `DLH-R-SUPERSET` | `DLH-X-OIDC` | authenticates dashboard users when external OIDC is used |
| `DLH-R-DATAHUB` | `DLH-R-KEYCLOAK` | authenticates catalog users when bundled Keycloak is used |
| `DLH-R-DATAHUB` | `DLH-X-OIDC` | authenticates catalog users when external OIDC is used |
| `DLH-R-VAULT` | `DLH-R-KEYCLOAK` | authenticates Vault users when bundled Keycloak is used |
| `DLH-R-VAULT` | `DLH-X-OIDC` | authenticates Vault users when external OIDC is used |
| `DLH-R-KEYCLOAK` | `DLH-X-LDAP` | federates users and groups when external LDAP is configured |
| `DLH-R-KEYCLOAK` | `DLH-R-KEYCLOAK-DB` | persists identity state |
| `DLH-X-SECRET-SYNC` | `DLH-R-VAULT` | reads selected secrets when included Vault is used |
| `DLH-X-SECRET-SYNC` | `DLH-R-KEYCLOAK` | provides Kubernetes Secrets |
| `DLH-X-SECRET-SYNC` | `DLH-R-RANGER` | provides Kubernetes Secrets |
| `DLH-X-SECRET-SYNC` | `DLH-R-TRINO` | provides Kubernetes Secrets |
| `DLH-X-SECRET-SYNC` | `DLH-R-HIVE` | provides Kubernetes Secrets |
| `DLH-X-SECRET-SYNC` | `DLH-R-PREFECT-SERVER` | provides Kubernetes Secrets |
| `DLH-R-RANGER` | `DLH-R-RANGER-DB` | persists policies and audit |
| `DLH-R-TRINO` | `DLH-R-RANGER` | checks authorization and masking |
| `DLH-R-TRINO` | `DLH-R-HIVE` | reads table metadata |
| `DLH-R-HIVE` | `DLH-R-HIVE-DB` | persists metastore data |
| `DLH-R-TRINO` | `DLH-R-MINIO` | reads and writes objects when MinIO is enabled |
| `DLH-R-TRINO` | `DLH-X-OBJECT-STORAGE` | reads and writes objects when external S3 is used |
| `DLH-R-HIVE` | `DLH-R-MINIO` | uses object storage for table data when MinIO is enabled |
| `DLH-R-HIVE` | `DLH-X-OBJECT-STORAGE` | uses object storage for table data when external S3 is used |
| `DLH-R-SUPERSET` | `DLH-R-TRINO` | queries governed datasets |
| `DLH-R-SUPERSET` | `DLH-R-SUPERSET-DB` | persists dashboards |
| `DLH-R-SUPERSET` | `DLH-R-SUPERSET-REDIS` | uses cache and queue |
| `DLH-R-JUPYTERHUB` | `DLH-R-JUPYTER-PODS` | spawns notebook servers |
| `DLH-R-JUPYTER-PODS` | `DLH-R-TRINO` | queries governed datasets |
| `DLH-R-CLOUDBEAVER` | `DLH-R-TRINO` | queries governed datasets |
| `DLH-X-PIPELINE-CODE` | `DLH-R-PREFECT-SERVER` | registers reviewed deployments |
| `DLH-R-PREFECT-SERVER` | `DLH-R-PREFECT-DB` | persists orchestration state |
| `DLH-R-PREFECT-WORKER` | `DLH-R-PREFECT-SERVER` | polls for flow runs |
| `DLH-R-PREFECT-WORKER` | `DLH-X-SOURCE-SYSTEMS` | extracts source data |
| `DLH-R-PREFECT-WORKER` | `DLH-R-MINIO` | writes lakehouse objects when MinIO is enabled |
| `DLH-R-PREFECT-WORKER` | `DLH-X-OBJECT-STORAGE` | writes lakehouse objects when external S3 is used |
| `DLH-R-PREFECT-WORKER` | `DLH-R-TRINO` | registers and transforms tables |
| `DLH-R-PREFECT-WORKER` | `DLH-R-SPARK-OPERATOR` | submits Spark jobs |
| `DLH-R-DATAHUB` | `DLH-R-DATAHUB-MYSQL` | persists metadata state |
| `DLH-R-DATAHUB` | `DLH-R-DATAHUB-KAFKA` | publishes and consumes metadata events |
| `DLH-R-DATAHUB` | `DLH-R-DATAHUB-ELASTICSEARCH` | indexes metadata for search |
| `DLH-X-PIPELINE-CODE` | `DLH-R-DATAHUB` | publishes product metadata when enabled |

### Layout

Put `Trino` in the centre with `Hive Metastore`, `MinIO`, and external S3 near
it as conditional data-plane paths. Put `Ranger` above Trino,
`Keycloak`/external OIDC and auth proxies above the browser tools, and `Prefect`
plus `Spark Operator` below the data plane. Put optional `DataHub` to the right
so it reads as an add-on discovery layer, not as a required data-mesh governance
service.

---

## Level 3 Component Diagram A: Chart Source

Parent Level 2 object: `DLH-C2-CHART-SOURCE`.

### Components

| ID | Name | Path | Description |
| --- | --- | --- | --- |
| `DLH-C3-SOURCE-METADATA` | Chart Metadata | `charts/dlh-in-a-box/Chart.yaml` | Declares the chart identity and its Helm dependencies, component names, repositories, and activation conditions. |
| `DLH-C3-SOURCE-LOCK` | Chart Lock | `charts/dlh-in-a-box/Chart.lock` | Records exact dependency versions and digests, providing reproducible dependency resolution. |
| `DLH-C3-SOURCE-VALUES` | Values Contract | `charts/dlh-in-a-box/values.yaml`; `charts/dlh-in-a-box/values.schema.json` | Defines the default settings and supported user-facing settings schema used to render the chart. |
| `DLH-C3-SOURCE-PACKAGING` | Packaging Controls | `charts/dlh-in-a-box/.helmignore` | Specifies files excluded from distributed chart archives, limiting package contents to deployable material. |
| `DLH-C3-SOURCE-DOCS` | Chart Guide And Notices | `charts/dlh-in-a-box/README.md`; `LICENSE`; `THIRD_PARTY_NOTICES.md` | Provides chart-local operating guidance, licensing information, and third-party notices for redistributed material. |
| `DLH-C3-SOURCE-STATIC-FILES` | Static Payload Files | `charts/dlh-in-a-box/files/` | Contains non-template files copied into generated Kubernetes objects, including Platform Home application assets. |
| `DLH-C3-SOURCE-PROVENANCE` | Third-Party Provenance | `charts/dlh-in-a-box/third_party/` | Stores bundled third-party license and notice material needed to document redistributed dependencies. |
| `DLH-C3-SOURCE-TEMPLATES` | Umbrella Templates | `charts/dlh-in-a-box/templates/` | Repository-owned Helm templates that adapt and coordinate dependency charts into a coherent runtime. |
| `DLH-C3-SOURCE-IDENTITY` | Identity Validation Templates | `charts/dlh-in-a-box/templates/identity-validation.yaml` | Validate identity-provider settings, including OIDC settings, LDAP integration, clients, redirect URIs, and group conventions. |
| `DLH-C3-SOURCE-GOVERNANCE` | Governance Validation Templates | `charts/dlh-in-a-box/templates/governance-validation.yaml` | Validate authorization settings, including roles, Ranger integration, catalog definitions, and policy settings. |
| `DLH-C3-SOURCE-RANGER` | Ranger Automation Templates | `charts/dlh-in-a-box/templates/ranger-automation.yaml`; `ranger-admin.yaml`; `_ranger-admin.tpl` | Generate Kubernetes resources that bootstrap, synchronize, administer, and audit Ranger policy state. |
| `DLH-C3-SOURCE-RANGER-PROXY` | Ranger Browser Proxy Templates | `charts/dlh-in-a-box/templates/ranger-browser-proxy.yaml` | Render oauth2-proxy resources that protect the Ranger administrative browser interface. |
| `DLH-C3-SOURCE-CLOUDBEAVER` | CloudBeaver Templates | `charts/dlh-in-a-box/templates/cloudbeaver.yaml` | Configure CloudBeaver workspace initialization, Trino connection definitions, user permissions, and authentication proxy integration. |
| `DLH-C3-SOURCE-HOME` | Platform Home Templates | `charts/dlh-in-a-box/templates/platform-home.yaml` | Render the platform portal, launcher settings, runtime settings, and health-check endpoints. |
| `DLH-C3-SOURCE-DATAHUB` | DataHub Auth And Compat Templates | `charts/dlh-in-a-box/templates/datahub-auth-secrets.yaml`; `datahub-prerequisites-compat.yaml` | Provide DataHub authentication secrets and compatibility resources for optional DataHub prerequisite services. |

### Relationships

| From | To | Label |
| --- | --- | --- |
| `DLH-C3-SOURCE-METADATA` | `DLH-C3-SOURCE-LOCK` | resolves to |
| `DLH-C3-SOURCE-PACKAGING` | `DLH-C3-SOURCE-METADATA` | constrains package content for |
| `DLH-C3-SOURCE-PROVENANCE` | `DLH-C3-SOURCE-DOCS` | supplies notices for |
| `DLH-C3-SOURCE-VALUES` | `DLH-C3-SOURCE-TEMPLATES` | configures |
| `DLH-C3-SOURCE-VALUES` | `DLH-C3-SOURCE-IDENTITY` | configures |
| `DLH-C3-SOURCE-VALUES` | `DLH-C3-SOURCE-GOVERNANCE` | configures |
| `DLH-C3-SOURCE-GOVERNANCE` | `DLH-C3-SOURCE-RANGER` | constrains |
| `DLH-C3-SOURCE-GOVERNANCE` | `DLH-C3-SOURCE-RANGER-PROXY` | constrains |
| `DLH-C3-SOURCE-IDENTITY` | `DLH-C3-SOURCE-CLOUDBEAVER` | constrains |
| `DLH-C3-SOURCE-IDENTITY` | `DLH-C3-SOURCE-HOME` | constrains |
| `DLH-C3-SOURCE-IDENTITY` | `DLH-C3-SOURCE-DATAHUB` | constrains |
| `DLH-C3-SOURCE-STATIC-FILES` | `DLH-C3-SOURCE-HOME` | provides payloads for |

---

## Level 3 Component Diagram B: Packaged Upstream Dependencies

Parent Level 2 object: `DLH-C2-UPSTREAM-ARCHIVES`.

### Components

| ID | Name | Path | Description |
| --- | --- | --- | --- |
| `DLH-C3-PKG-SUPERSET` | Superset Chart Archive | `charts/dlh-in-a-box/charts/superset-0.15.2.tgz` | Bundled Helm archive for the upstream Superset service, enabling optional dashboarding and business-intelligence deployment. |
| `DLH-C3-PKG-PREFECT-SERVER` | Prefect Server Chart Archive | `charts/dlh-in-a-box/charts/prefect-server-2025.12.31221620.tgz` | Bundled Helm archive for the upstream Prefect Server service, enabling workflow orchestration. |
| `DLH-C3-PKG-PREFECT-WORKER` | Prefect Worker Chart Archive | `charts/dlh-in-a-box/charts/prefect-worker-2025.12.31221620.tgz` | Bundled Helm archive for the upstream Prefect Worker service, enabling Kubernetes-based workflow execution. |
| `DLH-C3-PKG-OAUTH2-PROXY` | oauth2-proxy Chart Archive | `charts/dlh-in-a-box/charts/oauth2-proxy-10.1.4.tgz` | Bundled Helm archive for oauth2-proxy instances that protect browser-facing services with OIDC authentication. |
| `DLH-C3-PKG-KEYCLOAK` | Keycloak Chart Archive | `charts/dlh-in-a-box/charts/keycloak-25.2.0.tgz` | Bundled Helm archive for the upstream Keycloak identity provider used when OIDC is included with the deployment. |
| `DLH-C3-PKG-SPARK` | Spark Operator Chart Archive | `charts/dlh-in-a-box/charts/spark-operator-2.4.0.tgz` | Bundled Helm archive for the upstream Spark Operator, enabling Kubernetes-native management of Spark applications. |
| `DLH-C3-PKG-MINIO` | MinIO Chart Archive | `charts/dlh-in-a-box/charts/minio-15.0.7.tgz` | Bundled Helm archive for the upstream MinIO object store used when lakehouse data is stored inside the cluster. |
| `DLH-C3-PKG-DATAHUB` | DataHub Chart Archive | `charts/dlh-in-a-box/charts/datahub-0.8.21.tgz` | Bundled Helm archive for optional DataHub metadata catalog and discovery services. |
| `DLH-C3-PKG-DATAHUB-PREREQS` | DataHub Prerequisites Chart Archive | `charts/dlh-in-a-box/charts/datahub-prerequisites-0.2.3.tgz` | Bundled Helm archive for optional DataHub support services, including persistence, messaging, and search dependencies. |
| `DLH-C3-PKG-VAULT` | Vault Chart Archive | `charts/dlh-in-a-box/charts/vault-0.32.0.tgz` | Bundled Helm archive for optional Vault secret-management deployment included with the chart. |
| `DLH-C3-PKG-JUPYTERHUB` | JupyterHub Chart Archive | `charts/dlh-in-a-box/charts/jupyterhub-4.3.3.tgz` | Bundled Helm archive for the upstream JupyterHub service, enabling authenticated multi-user notebook environments. |
| `DLH-C3-PKG-POSTGRESQL` | PostgreSQL Chart Archive | `charts/dlh-in-a-box/charts/postgresql-14.3.3.tgz` | Bundled Helm archive for the upstream PostgreSQL chart reused by service-specific database components. |

Draw these as contained archive components. You usually do not need arrows
between the archive components.

---

## Level 3 Component Diagram C: Vendored Trino Chart

Parent Level 2 object: `DLH-C2-TRINO-VENDORED`.

### Components

| ID | Name | Path | Description |
| --- | --- | --- | --- |
| `DLH-C3-TRINO-DOCS` | Trino Integration Documentation | `charts/dlh-in-a-box/charts/trino/OVERVIEW.md`; `templates/_README.txt` | Explains why the local Trino chart is included and documents the supported integration boundary. |
| `DLH-C3-TRINO-HELPERS` | Trino Integration Helpers | `charts/dlh-in-a-box/charts/trino/templates/_helpers.tpl` | Defines shared templating functions used by the local Trino integration. |
| `DLH-C3-TRINO-CATALOGS` | Trino Catalog Rendering | `charts/dlh-in-a-box/charts/trino/templates/configmap-catalog.yaml` | Generates Trino catalog settings, mapping chart settings to catalog properties for object-backed datasets. |
| `DLH-C3-TRINO-ACCESS` | Trino Access-Control Rendering | `charts/dlh-in-a-box/charts/trino/templates/configmap-access-control-*.yaml` | Generates Trino access-control settings, including file-based rules or Ranger-backed authorization. |
| `DLH-C3-TRINO-COORDINATOR` | Trino Coordinator Rendering | `charts/dlh-in-a-box/charts/trino/templates/deployment-coordinator.yaml` | Renders the Trino coordinator deployment and wires identity, credentials, catalog, access-control, and object-storage settings. |
| `DLH-C3-TRINO-WORKER` | Trino Worker Rendering | `charts/dlh-in-a-box/charts/trino/templates/deployment-worker.yaml` | Renders Trino worker deployments with the identity, credential, catalog, and storage integration required for distributed query execution. |

### Relationships

| From | To | Label |
| --- | --- | --- |
| `DLH-C3-TRINO-HELPERS` | `DLH-C3-TRINO-CATALOGS` | supports rendering |
| `DLH-C3-TRINO-HELPERS` | `DLH-C3-TRINO-ACCESS` | supports rendering |
| `DLH-C3-TRINO-HELPERS` | `DLH-C3-TRINO-COORDINATOR` | supports rendering |
| `DLH-C3-TRINO-HELPERS` | `DLH-C3-TRINO-WORKER` | supports rendering |
| `DLH-C3-TRINO-CATALOGS` | `DLH-C3-TRINO-COORDINATOR` | configures |
| `DLH-C3-TRINO-ACCESS` | `DLH-C3-TRINO-COORDINATOR` | configures |
| `DLH-C3-TRINO-ACCESS` | `DLH-C3-TRINO-WORKER` | configures |

---

## Level 3 Component Diagram D: Hive Metastore Local Subchart

Parent Level 2 object: `DLH-C2-HIVE-SUBCHART`.

### Components

| ID | Name | Path | Description |
| --- | --- | --- | --- |
| `DLH-C3-HIVE-DOCS` | Hive Subchart Documentation | `charts/dlh-in-a-box/charts/hive/README.md`; `templates/_README.txt` | Defines the purpose and ownership boundary of the first-party Hive Metastore subchart. |
| `DLH-C3-HIVE-METADATA` | Hive Chart Metadata | `charts/dlh-in-a-box/charts/hive/Chart.yaml` | Declares the local subchart identity, version, and chart metadata. |
| `DLH-C3-HIVE-VALUES` | Hive Values | `charts/dlh-in-a-box/charts/hive/values.yaml` | Defines Hive-specific defaults, including metastore, database, and object-storage settings. |
| `DLH-C3-HIVE-HELPERS` | Hive Helpers | `charts/dlh-in-a-box/charts/hive/templates/_helpers.tpl` | Provides template helpers for naming, secret lookup, S3 settings, PostgreSQL settings, and checksum annotations. |
| `DLH-C3-HIVE-CONFIG` | Hive Config Rendering | `charts/dlh-in-a-box/charts/hive/templates/configmap.yaml` | Generates Hive Metastore settings for database connectivity and object-storage access. |
| `DLH-C3-HIVE-METASTORE` | Hive Metastore Runtime Rendering | `charts/dlh-in-a-box/charts/hive/templates/metastore.yaml` | Renders the Kubernetes Service, Deployment, volume mounts, probes, and optional ingress for Hive Metastore. |
| `DLH-C3-HIVE-SCHEMA` | Hive Schema Initialization | `charts/dlh-in-a-box/charts/hive/templates/init-*.yaml` | Initializes or validates the relational schema required by the Hive Metastore database. |
| `DLH-C3-HIVE-SECRETS` | Hive Secret Rendering | `charts/dlh-in-a-box/charts/hive/templates/*secret*.yaml` | Generates Kubernetes Secrets for database and object-storage credentials used by Hive. |

### Relationships

| From | To | Label |
| --- | --- | --- |
| `DLH-C3-HIVE-VALUES` | `DLH-C3-HIVE-CONFIG` | configures |
| `DLH-C3-HIVE-HELPERS` | `DLH-C3-HIVE-CONFIG` | supports rendering |
| `DLH-C3-HIVE-HELPERS` | `DLH-C3-HIVE-METASTORE` | supports rendering |
| `DLH-C3-HIVE-SECRETS` | `DLH-C3-HIVE-METASTORE` | provides credentials |
| `DLH-C3-HIVE-CONFIG` | `DLH-C3-HIVE-METASTORE` | configures |
| `DLH-C3-HIVE-SCHEMA` | `DLH-C3-HIVE-METASTORE` | prepares database schema |

---

## Level 3 Component Diagram E: Validation And Publish Automation

Parent Level 2 objects: `DLH-C2-VALIDATION` and `DLH-C2-PUBLISH`. Use two
small diagrams if IcePanel does not allow one component diagram to cover both
applications.

### Validation Components

| ID | Name | Parent | Path | Description |
| --- | --- | --- | --- | --- |
| `DLH-C3-VALIDATE-LINT` | Helm Lint Workflow | `DLH-C2-VALIDATION` | `.github/workflows/helm-lint.yaml`; `hack/lint.sh` | Runs automated checks for licensing, documentation, security, rendering rules, shell scripts, JSON schema, and Helm syntax. |
| `DLH-C3-VALIDATE-DEPS` | Dependency Refresh Check | `DLH-C2-VALIDATION` | `hack/helm-dependency-update.sh`; `Chart.lock` | Refreshes Helm dependency archives and updates lock metadata so packaged dependencies remain reproducible. |
| `DLH-C3-VALIDATE-RENDER` | Example Render Checks | `DLH-C2-VALIDATION` | `hack/template.sh`; `examples/*.yaml` | Renders every maintained example configuration file to verify that supported installation profiles produce valid manifests. |
| `DLH-C3-VALIDATE-CONTRACT` | Render Contract Checks | `DLH-C2-VALIDATION` | `test/render-contract.sh`; `test/render-contract/` | Verifies expected render outputs and expected failure modes for the chart's documented configuration rules. |
| `DLH-C3-VALIDATE-SMOKE` | Smoke Install Workflow | `DLH-C2-VALIDATION` | `.github/workflows/helm-smoke-install.yaml`; `hack/smoke-install.sh` | Installs an identity- and governance-oriented local profile into a disposable cluster to test an integrated runtime path. |

### Publish Components

| ID | Name | Parent | Path | Description |
| --- | --- | --- | --- | --- |
| `DLH-C3-PUBLISH-PACKAGE` | Helm Package Step | `DLH-C2-PUBLISH` | `hack/package.sh`; `dist/` | Builds the versioned Helm chart archive for release. |
| `DLH-C3-PUBLISH-OCI` | OCI Push Step | `DLH-C2-PUBLISH` | `.github/workflows/helm-publish.yaml` | Publishes the release chart package to the GHCR OCI registry. |
| `DLH-C3-PUBLISH-METADATA` | Release Metadata Step | `DLH-C2-PUBLISH` | `.github/release.yml`; `Chart.yaml` annotations | Records chart version, labels, annotations, and release metadata used by deployment repositories. |

### Relationships

| From | To | Label |
| --- | --- | --- |
| `DLH-C3-VALIDATE-DEPS` | `DLH-C3-VALIDATE-LINT` | prepares dependencies for |
| `DLH-C3-VALIDATE-LINT` | `DLH-C3-VALIDATE-RENDER` | runs before |
| `DLH-C3-VALIDATE-RENDER` | `DLH-C3-VALIDATE-CONTRACT` | provides rendered manifests for |
| `DLH-C3-VALIDATE-CONTRACT` | `DLH-C3-VALIDATE-SMOKE` | must pass before |
| `DLH-C3-PUBLISH-PACKAGE` | `DLH-C3-PUBLISH-OCI` | produces package for |
| `DLH-C3-PUBLISH-OCI` | `DLH-C3-PUBLISH-METADATA` | records |

---

## What Not To Show Here

| Do Not Model As Internal | Reason |
| --- | --- |
| Sanger OpenStack, Cinder/Ceph, Sanger DNS, Sanger PKI | Deployment infrastructure, not DLH-in-a-box product internals. |
| icddr,b VMware, vSphere CSI, icddr,b DNS/TLS | Production infrastructure, not chart internals. |
| `platform/dlh-in-a-box/values-dev.yaml` and `values-prod.yaml` | Institution-specific settings, not upstream chart source. |
| PaM and ICDDRB realms | Data mesh/domain architecture, not the chart product. |
| Project-specific Prefect flows and dbt models | Pipeline repository content that runs on the platform. |
| DataHub as mandatory mesh registry | It is currently optional and deployment-controlled. |
