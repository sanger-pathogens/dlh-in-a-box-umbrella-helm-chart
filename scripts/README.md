# Maintainer Scripts

This folder contains the local scripts that check, render, package, and test
the chart.

If you are maintaining this repo, this folder is your operational toolbox.

## Who Should Read This

| Reader | Why this guide matters |
| --- | --- |
| contributor | to know which script to run before opening a change |
| maintainer | to understand CI parity, side effects, and failure modes |
| reviewer | to see what local evidence a change should come with |

```mermaid
flowchart TD
  subgraph Inputs["Inputs"]
    Source[chart source and example files]
  end

  subgraph RepoScripts["Repo Scripts"]
    Docs[docs-check.sh]
    Security[security-check.sh]
    License[license-check.sh]
  end
  subgraph HelmScripts["Helm scripts"]
    Deps[helm-dependency-update.sh]
    Template[template.sh]
    Package[package.sh]
    Smoke[smoke-install.sh]
  end
  Lint[lint.sh]

  subgraph Outputs["Outputs"]
    Lockfiles[updated Chart.lock and archives]
    Rendered[rendered manifests]
    PackageOut[chart package]
    SmokeRun[local smoke install]
    ValidatedChart[validated chart and repo structure]
  end

  Source --> Deps
  Source --> Docs
  Source --> Lint
  Source --> Template
  Source --> Package
  Source --> Smoke
  Deps --> Lockfiles
  Docs --> Lint
  Security --> Lint
  License --> Lint
  Template --> Rendered
  Template --> Package
  Package --> PackageOut
  Smoke --> SmokeRun
  Lint --> ValidatedChart
```

## What Lives In This Folder

| Path    | Purpose                                |
|---------|----------------------------------------|
| `helm/` | Helper scripts that wrap helm commands |
| `repo/` | Scripts to validate repo structure and standards |

## How The Scripts Fit Together

The scripts are divided into two subdirectories, joined by `verify.sh`

`helm/` is for scripts that wrap helm commands, such as helm package or helm lint.
`repo/` is for scripts that enforce repo structure and policies, for example presence and contents
of repo guide files, and presence of required license files.

## Script Behaviour
See the guide files for subdirectories of scripts for documentation on individual maintainer scripts.

### `verify.sh`

What it does:

- runs `repo/license-check.sh`
- runs `repo/docs-check.sh`
- runs `repo/security-check.sh`
- runs `../test/render-contract.sh`
- syntax-checks shell scripts
- parses `values.schema.json`
- runs `helm lint` for the chart alone and then against every example overlay

This is the main local validation entrypoint mirrored by CI.

## Pre-Commit Hooks
Some of these maintainer scripts are used as Git pre-commit hooks. On each commit, this repo's pre-commit hooks will:
- Validate syntax across maintainer scripts
- Run `repo/license-check.sh`
- Run `helm/helm-dependency-update.sh` only if `Chart.yaml` or `Chart.lock` changed
- Run `repo/docs-check.sh`
- Validate Mermaid diagrams only if `*.md` files changed
- Run `helm/helm-lint.sh`
- Run `repo/security-check.sh`
- Run `helm/template.sh`
- Run `shellcheck` on all shell scripts

To use the hooks, ensure pre-commit is installed. Use a system-wide install via brew or another package manager of choice,
or install `pre-commit` to a local python venv.

To activate the hooks:
```commandline
pre-commit install
```
To run the hooks at any point, use `pre-commit` to run on staged files, or `pre-commit run -a` to run on all files.

On first run, these hooks may take a couple of minutes to install and run the helm dependency update and Mermaid validate steps.
Subsequent runs will be much faster, especially if the chart and mermaid diagrams have not changed.

## The Main Local Validation Path

From the repository root:

```bash
./scripts/helm/helm-dependency-update.sh
./scripts/repo/docs-check.sh
./scripts/verify.sh
./scripts/helm/template.sh
./scripts/helm/package.sh
```

If you changed sign-in, access rules, browser proxies, or the local auth
overlay, also run:

```bash
make smoke-install
```

If you want a thin local wrapper without smoke semantics, `make local-install`
exists in the root `Makefile`, but it should not be treated as equivalent to
`smoke-install`.

## CI Parity

The GitHub workflows intentionally mirror these scripts instead of re-encoding
the logic in YAML.

Closest matches:

- `.github/workflows/helm-lint.yaml` mirrors `deps`, `lint`, `template`, and
  `package`
- `.github/workflows/helm-smoke-install.yaml` mirrors `smoke-install`
- `.github/workflows/helm-publish.yaml` uses `deps`, `lint`, and `package`
  before pushing to GHCR

When a workflow changes, check the matching script here first. The repo expects
local and CI behavior to stay aligned.

## Common Tasks

If you need to:

- prove docs are still structurally valid: run `./scripts/repo/docs-check.sh`
- check one example overlay only: run `./scripts/helm/template.sh examples/my-file.yaml`
- build a chart package with explicit versions: run
  `./scripts/helm/package.sh charts/dlh-in-a-box dist <chart-version> <app-version>`
- debug a failing local auth install: run `make smoke-install` with
  `ARTIFACT_DIR` set so diagnostics are saved

## Common Mistakes

- treating `helm/smoke-install.sh` as equivalent to a simple manual `helm install`
- forgetting that `verify.sh` already runs several other scripts
- changing dependencies without refreshing `Chart.lock` and packaged archives
- debugging auth changes with `values-local.yaml` instead of the smoke path
- adding large real-world YAML examples under `/testdata/`
- assuming local Mermaid validation works without Docker

## When You Can Ignore This Folder

You can ignore this folder only if you are consuming a published chart and do
not intend to validate or maintain the repo locally.

If you are contributing, this folder should become familiar quickly because it
defines what “done” looks like for a change.
