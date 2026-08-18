# Contributing

This file is for people changing the repo.

The repo is public to read, but pull requests are mainly for repository
collaborators.

If you are not a collaborator, use [SUPPORT.md](SUPPORT.md) instead of
assuming you can open a pull request.

## Local workflow

Install the pre-commit hooks: 
```commandline
pre-commit install
```
Then, to validate changes:
```commandline
pre-commit run
```

Alternatively, use the make target to run all the checks:
```bash
make verify
```

Use `make smoke-install` too when you changed:

- sign-in behavior
- access rules
- example values files
- local smoke-install behavior
- scripts or workflows

The smoke path installs `examples/values-local-auth.yaml` and creates the demo
Secrets that file needs.

## Keep These Things In Sync

Good changes usually update these together:

- chart behavior
- example settings files
- folder guide files
- local scripts and workflow docs

## Dependency updates

- When you change chart dependencies, run
  `scripts/helm/helm-dependency-update.sh` so `Chart.lock` and packaged dependency
  archives stay aligned.
- Review upstream release notes and licenses before upgrading dependencies.

## Versioning and publication

- Pushes to `main` publish a unique prerelease version to GHCR.
- Tags in the form `vX.Y.Z` publish the stable `X.Y.Z` version.
- Stable releases should keep `charts/dlh-in-a-box/Chart.yaml` in sync with
  the Git tag used for publication.

## Ownership

- Repository ownership is managed in `.github/CODEOWNERS`.
- Default code owner is the
  `@sanger-pathogens/data-engineering-and-integration-sanger` team.

## Contribution model

- This repository may be public to read, but pull requests are mainly limited
  to repository collaborators.
- External readers should not assume that public visibility means open write
  access.
- Non-collaborators should use the issue templates or support path.
- Review routing and stewardship live in `.github/CODEOWNERS`.
- Public issue intake is handled through `.github/ISSUE_TEMPLATE/`.

## Pull requests

Good pull requests for this repository usually include:

- a short explanation of the chart-facing change
- example or guide updates when behavior changed
- note of dependency or license impact, if any
- updates to local directory guides when repository structure changes
