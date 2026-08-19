# Umbrella Templates

This folder contains the Helm templates that are fully owned by this repo.

Read this guide when you need to understand where the umbrella chart adds
behavior that upstream dependency charts do not provide on their own.

## Who Should Read This

| Reader | Why this guide matters |
| --- | --- |
| contributor | to know which repo-owned template owns identity, governance, browser, or Ranger behavior |
| operator | to understand where fail-fast validation and helper-generated resources come from |
| maintainer | to see which files are safe to edit here instead of patching an upstream dependency |

## What This Folder Solves

The umbrella chart uses upstream charts for many components, but the platform
still needs cross-cutting behavior that no dependency chart can own by itself.

Examples:

- validating shared identity and governance rules before Helm renders anything
- generating a repo-specific browser landing page and helper API
- wrapping CloudBeaver and Ranger with repo-specific auth behavior
- reconciling Ranger roles and policies from the chart's governance model
- smoothing compatibility gaps for DataHub prerequisites

```mermaid
flowchart TD
  subgraph Inputs["Umbrella inputs"]
    Identity[global identity]
    Authorization[global authorization]
    Catalogs[global data catalogs]
    Apps[platform apps and wrappers]
  end

  subgraph Templates["Repo-owned templates"]
    Helpers[shared helpers]
    Validation[identity and governance validation]
    Platform[platformHome and CloudBeaver]
    Ranger[Ranger admin automation and browser proxy]
    DataHub[DataHub helper resources]
    Notes[install notes]
  end

  subgraph Outcome["Rendered result"]
    Failures[fail-fast Helm errors]
    Resources[workloads services secrets config]
    InstallNotes[post-install guidance]
  end

  Identity --> Helpers
  Identity --> Validation
  Authorization --> Helpers
  Authorization --> Validation
  Catalogs --> Validation
  Identity --> Platform
  Apps --> Platform
  Authorization --> Ranger
  Catalogs --> Ranger
  Apps --> DataHub
  Helpers --> Platform
  Helpers --> Ranger
  Helpers --> DataHub
  Validation --> Failures
  Platform --> Resources
  Ranger --> Resources
  DataHub --> Resources
  Notes --> InstallNotes
```

## What Lives In This Folder

| File | Ownership | What it is for |
| --- | --- | --- |
| `_helpers.tpl` | repo-owned | shared naming, URL, secret, identity, directory, and group helpers used across the umbrella chart |
| `_ranger-admin.tpl` | repo-owned | helper text blocks for Ranger Admin bootstrap files |
| `identity-validation.yaml` | repo-owned | fail-fast contract checks for shared identity modes and app wiring |
| `authorization-validation.yaml` | repo-owned | fail-fast contract checks for catalog and Ranger authorization settings |
| `platform-home.yaml` | repo-owned | inline launchpad UI plus helper API and access-control admin behavior |
| `cloudbeaver.yaml` | repo-owned | CloudBeaver service, config, storage, bootstrap, trust-store, and optional ingress wiring |
| `ranger-admin.yaml` | repo-owned | Ranger Admin bootstrap ConfigMap, Service, and Deployment |
| `ranger-automation.yaml` | repo-owned | role and policy reconciliation, LDAP or local user sync, and exception audits |
| `ranger-browser-proxy.yaml` | repo-owned | small nginx proxy that makes Ranger Admin usable behind browser auth |
| `datahub-auth-secrets.yaml` | repo-owned | stable generated secrets for DataHub internal auth |
| `datahub-prerequisites-compat.yaml` | repo-owned | compatibility aliases for DataHub prerequisites naming and MySQL secret expectations |
| `NOTES.txt` | repo-owned | post-install Helm output |

Nothing in this folder is vendored. If you need to change one of these files,
you are editing first-party repo behavior.

## How These Templates Fit Into The Chart

The easiest way to think about this folder is by responsibility:

- `_helpers.tpl` and `_ranger-admin.tpl` define reusable building blocks
- `identity-validation.yaml` and `authorization-validation.yaml` reject invalid
  values combinations before resources render
- `platform-home.yaml`, `cloudbeaver.yaml`, and `ranger-browser-proxy.yaml`
  own browser-facing repo-specific apps and wrappers
- `ranger-admin.yaml` and `ranger-automation.yaml` own governance control-plane
  services that are specific to this platform model
- `datahub-auth-secrets.yaml` and `datahub-prerequisites-compat.yaml` bridge
  awkward dependency integration gaps

## File-By-File Behavior

### `_helpers.tpl`

This is the backbone of the umbrella chart.

It contains helpers that other files rely on for:

- release naming
- URL and hostname generation
- identity provider and directory lookup
- secret-name resolution
- shared platform group naming
- service-name construction for repo-owned components

If multiple templates need the same naming or decision logic, the change
usually belongs here instead of being duplicated.

### `_ranger-admin.tpl`

This file holds large text helpers that would be awkward to keep inline inside
`ranger-admin.yaml`.

It is where the repo defines the generated `install.properties` and startup
script content used to bootstrap Ranger Admin against PostgreSQL and the repo's
service URLs.

Edit this file when you need to change the generated Ranger bootstrap files,
not when you need to change the Deployment shell around them.

### `identity-validation.yaml`

This file is one of the highest-value safety rails in the repo.

It does not render a long-lived workload. Instead, it fails Helm rendering when
the identity contract is invalid.

Important behaviors checked here include:

- `global.identity` must live under `global`, not old top-level keys
- supported environment names for shared identity
- bundled Keycloak requirements such as `keycloak.enabled`,
  `keycloakConfigCli.enabled`, and matching config CLI secret names
- directory-mode restrictions such as `keycloakLocal` versus `externalLdap`
- required LDAP settings when shared identity depends on an organizational
  directory
- required redirect URIs and web origins for bundled Keycloak-managed clients
- app-specific contracts for JupyterHub, Superset, DataHub, platformHome,
  CloudBeaver, Ranger proxy, and Prefect auth clients
- restrictions on wildcard redirect URIs outside local environments
- bootstrap-user fallback restrictions for local or dev-only auth paths

If a newcomer sees `helm template` fail before any YAML is emitted, this file
is often why.

### `authorization-validation.yaml`

This file validates that catalog and Ranger authorization settings are
internally consistent before Ranger resources render.

Checks include:

- `global.environment` must be set to `local`, `dev`, or `prod` whenever
  `global.dataCatalogs` is non-empty
- deprecated catalog `authorizedGroups`/`authorizedUsers` ACL settings are
  rejected outside `local` (catalog access must go through Ranger roles)
- when Ranger is enabled, every role listed under a catalog's
  `authorizedRoles.read`/`.write` must be declared (and not disabled) under
  `global.authorization.ranger.dataRoles`

Dataset sensitivity/classification metadata (data type, IRB status, consent
basis, PHI identifiers, etc.) is not part of this chart; an institution
tracking that keeps it in whatever system owns the dataset's
schema/classification decisions.

### `platform-home.yaml`

This is the largest repo-owned template in the chart and one of the most
under-documented pieces of the platform.

It does much more than render a static landing page. The template embeds:

- the HTML, CSS, and JavaScript for the launchpad page
- the optional Keycloak-backed login flow used by the browser UI
- helper API endpoints such as launcher and health-check routes
- the access-control admin UI and supporting API endpoints
- ConfigMap-backed state for generated access-control content
- service-account and token-aware logic for helper operations

Most of the runtime logic for `platformHome` lives inline here rather than in
`files/`, which is why the payload folder is intentionally tiny.

If you are changing layout, launch behavior, access-control editing, or helper
API logic, this is the file you need to read.

### `cloudbeaver.yaml`

This template renders the repo-managed CloudBeaver deployment shape.

It owns behavior that the upstream CloudBeaver image does not know about:

- generation of the main `cloudbeaver.conf`
- auth-proxy header mapping so browser identity arrives from oauth2-proxy
- optional workspace PVC creation
- bootstrap secret handling for initial admin and workspace data
- optional workspace seed secret injection
- optional trust-store generation from a provided CA certificate
- optional shared Trino connection seeding so users arrive with a prebuilt
  platform connection
- checksum annotations that force rollout when bootstrap or trust inputs change

Edit this file when you are changing how CloudBeaver is configured or seeded,
not when you are changing the standalone oauth2-proxy chart behavior.

### `ranger-admin.yaml`

This template is the runtime shell for Ranger Admin itself.

It renders:

- a ConfigMap containing generated bootstrap files
- the ClusterIP Service
- the Ranger Admin Deployment

It expects two important secret inputs:

- a PostgreSQL secret for the Ranger database
- a Ranger admin secret containing the admin password and, when enabled, the
  usersync and tagsync passwords

The actual generated bootstrap file contents come from `_ranger-admin.tpl`.

### `ranger-automation.yaml`

This file is the second large hidden-behavior template in the repo.

It renders a ConfigMap with generated JSON configuration plus embedded Python
automation code, then wires that code into reconciliation Jobs and CronJobs.

Important behavior owned here includes:

- bootstrap creation and reconciliation of Ranger service definitions
- creation and updating of platform roles
- mapping chart-defined platform roles and catalog metadata into Ranger roles
  and policies
- optional import of catalog ACLs
- LDAP usersync when the platform uses an organizational directory
- local-user sync when the platform is in `keycloakLocal` mode
- periodic exception-role audits with expiry handling

The rendered runtime shape is broader than one Job:

- a bootstrap ConfigMap containing JSON configuration and embedded Python code
- a bootstrap reconciliation Job
- a scheduled LDAP usersync CronJob when directory-backed sync is enabled
- a scheduled local-user sync CronJob in `keycloakLocal` mode
- a scheduled exception-role audit CronJob

If the repo's access model changes, this file usually changes with it.

### `ranger-browser-proxy.yaml`

Ranger Admin itself is not a polished end-user browser surface.

This template creates a small nginx Deployment and Service that:

- forwards browser traffic to Ranger Admin
- injects basic auth using the Ranger admin credentials
- provides a friendlier target for the external auth boundary

The oauth2-proxy in front of Ranger is still configured elsewhere. This file is
the bridge between that browser-facing auth layer and the underlying Ranger
Admin service.

### `datahub-auth-secrets.yaml`

DataHub expects a few internal secrets for token signing and internal auth.

This template creates them once and uses `lookup` so upgrades preserve existing
values instead of rotating them every render.

That makes it safe for repeated `helm upgrade` runs without destabilizing
DataHub's internal signing state.

### `datahub-prerequisites-compat.yaml`

This file exists because the umbrella chart and the bundled DataHub
prerequisites do not agree perfectly on names and secret shapes.

It creates compatibility resources such as:

- `ExternalName` Services with the names DataHub expects
- a `mysql-secrets` Secret alias when the real MySQL secret uses a different
  name

This is integration glue. If DataHub prerequisites naming changes upstream,
this file is one of the first places that needs review.

## Render-Time `lookup` Behavior

Several templates in this folder use Helm `lookup`.

That is deliberate, but it creates an important documentation nuance:

- `cloudbeaver.yaml` inspects existing secrets so checksum annotations reflect
  the real current secret payload
- `datahub-auth-secrets.yaml` preserves generated secret material across
  upgrades
- `datahub-prerequisites-compat.yaml` can copy values out of an existing MySQL
  secret when the dependency secret name does not match what DataHub expects

This means a dry `helm template` against an empty context can differ from an
upgrade against a namespace that already contains those secrets.

When debugging surprising diffs, check whether the template path is depending
on already-existing cluster state.

### `NOTES.txt`

This file controls the text Helm prints after install or upgrade.

Use it for operator guidance that is:

- specific to this umbrella chart
- short enough to be useful in terminal output
- tied to what the chart actually rendered

Do not turn it into a second README.

## Common Tasks

If you need to:

- add or change a shared naming rule: start in `_helpers.tpl`
- tighten or relax supported auth combinations: edit
  `identity-validation.yaml`
- change catalog or Ranger authorization rules: edit
  `authorization-validation.yaml`
- change the launchpad UI or helper API: edit `platform-home.yaml`
- change CloudBeaver seeding, trust, or auth-proxy integration: edit
  `cloudbeaver.yaml`
- change Ranger bootstrap scripts: edit `_ranger-admin.tpl`
- change Ranger runtime shell: edit `ranger-admin.yaml`
- change role or policy reconciliation: edit `ranger-automation.yaml`
- change DataHub compatibility or generated auth secrets: edit the relevant
  `datahub-*` file

## Validation

After changing anything in this folder, the fastest checks are:

```bash
./hack/render-contract.sh
./hack/template.sh
./hack/lint.sh
```

Use `./hack/smoke-install.sh charts/dlh-in-a-box examples/values-local-auth.yaml`
when you changed browser auth, launchpad behavior, or other runtime-heavy local
paths.

## Common Mistakes

- patching an upstream dependency chart when the behavior really belongs in
  this umbrella layer
- adding a new cross-component rule to `values.schema.json` alone without also
  enforcing it in validation templates
- forgetting that `platform-home.yaml` and `ranger-automation.yaml` contain
  large inline runtime code, not just Kubernetes YAML shell
- assuming Ranger governs Trino in every mode even when the chart is still
  using generated file-based access-control rules

## When You Can Ignore This Folder

You can ignore this folder if you only consume the chart and never need to
change repo-owned render logic.

You cannot ignore it if the question is, "Where does this platform-specific
behavior actually come from?"
