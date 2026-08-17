# Helm Scripts

This folder contains the local scripts that check, render, package, and test
the chart.

## What Lives In This Folder

| Script or path | Reads | Writes or side effects | Main job |
| --- | --- | --- | --- |
| `helm-dependency-update.sh` | `Chart.yaml` | updates `Chart.lock` and packaged archives | refresh dependencies |
| `template.sh` | chart and selected example files | manifests to stdout only | render the chart without installing it |
| `package.sh` | chart source | `dist/*.tgz` | create publishable chart package |
| `smoke-install.sh` | chart, one values file, current kube context | cluster resources, optional diagnostic artifacts | install locally and wait for readiness |

## How The Scripts Fit Together

The simplest mental model is:

- `template.sh` proves the tracked example overlays still render
- `package.sh` proves the chart can still be packaged
- `smoke-install.sh` is the heavy, cluster-touching end-to-end local auth test

## Script-By-Script Behavior

### `helm-dependency-update.sh`

What it does:

- runs `helm dependency update` for the umbrella chart
- refreshes `Chart.lock`
- refreshes packaged dependency archives under `charts/dlh-in-a-box/charts/`

Run this when:

- `Chart.yaml` dependency versions changed
- packaged archives and lockfile drifted
- a workflow or packager complains about dependency mismatch

Why it matters:

- the repo stores dependency archives for reproducible packaging
- version changes are incomplete until the lockfile and archives move too

### `template.sh`

What it does:

- runs `helm template` against all example overlays by default
- can also render only the files you pass as arguments

Use this when:

- changing templates
- changing values defaults
- changing example overlays

This is usually the fastest way to prove a change still renders without needing
to install anything.

### `package.sh`

What it does:

- packages the chart into `dist/`
- optionally overrides chart version and app version

Why the optional overrides exist:

- the publish workflow uses them to generate unique prerelease versions for
  pushes to `main`
- tagged releases use the chart version already stored in `Chart.yaml`

Exact argument shape:

- argument 1: chart path, default `charts/dlh-in-a-box`
- argument 2: destination directory, default `dist`
- argument 3: optional chart version override
- argument 4: optional app version override

### `smoke-install.sh`

What it does:

- optionally refreshes dependencies first
- optionally resets the release and namespace
- seeds demo secrets when the target values file is `values-local-auth.yaml`
- installs the chart with `helm upgrade --install`
- waits for Deployments, Jobs, and Pods to become ready
- retries a few common transient Kubernetes API failures
- captures diagnostics into `ARTIFACT_DIR` on failure

Why it is special:

- it is the heaviest local script in this repo
- it talks to a real cluster
- it is the script mirrored by the GitHub Actions smoke workflow

Important environment variables:

- `RELEASE_NAME`
- `NAMESPACE`
- `TIMEOUT`
- `ARTIFACT_DIR`
- `SKIP_DEPENDENCY_UPDATE`
- `RESET_RELEASE_STATE`

What those variables really mean:

- `RESET_RELEASE_STATE=true` uninstalls the release and deletes the namespace
  before reinstalling
- `SKIP_DEPENDENCY_UPDATE=true` skips the dependency refresh that normally
  happens first
- `ARTIFACT_DIR` turns on structured diagnostics capture including Helm status,
  rendered manifest, events, pod descriptions, and logs

Local-auth-only side effect:

- when the target file is exactly `values-local-auth.yaml`, the script seeds
  demo secrets such as `dlh-keycloak-admin`, `dlh-keycloak-config-cli-env`,
  `dlh-ranger-admin`, `dlh-cloudbeaver-oauth2-proxy`,
  `dlh-prefect-oauth2-proxy`, and `dlh-cloudbeaver-bootstrap`
- that secret seeding does not happen for the simpler local overlay or the
  shared-environment examples

Use this when:

- identity changed
- Ranger behavior changed
- auth proxies changed
- the local auth overlay changed
