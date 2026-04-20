# Contributing

Thanks for contributing to `dlh-in-a-box`.

This repository is intentionally focused on one job: maintaining and publishing
the reusable umbrella chart. Please keep changes aligned with that scope.

## Local workflow

Before opening a pull request, run the standard local checks:

```bash
./hack/helm-dependency-update.sh
SKIP_MERMAID_CHECK=1 ./hack/docs-check.sh
./hack/lint.sh
./hack/template.sh
./hack/package.sh
```

Equivalent convenience targets exist in the repository root:

```bash
make deps
make lint
make template
make package
```

Notes:

- `./hack/lint.sh` already includes docs, license, security, render-contract,
  schema, and Helm lint checks.
- full Mermaid rendering in `./hack/docs-check.sh` requires a working Docker
  daemon. `SKIP_MERMAID_CHECK=1` is the intentional local bypass when Docker
  is unavailable.
- the tracked example overlays under `examples/` are part of the supported
  contract and are exercised by the validation scripts.

For the simplest manual local install, use:

```bash
helm upgrade --install dlh charts/dlh-in-a-box \
  -n data-lakehouse-local \
  --create-namespace \
  -f examples/values-local.yaml
```

For the auth-enabled local proof path, use:

```bash
make smoke-install
```

That path installs `examples/values-local-auth.yaml` and seeds the demo
Secrets that overlay requires.

`make local-install` is lower-level. It does not create Secrets, and its
default `LOCAL_VALUES` points at `examples/values-local-auth.yaml`. Override
`LOCAL_VALUES=examples/values-local.yaml` for the simple self-contained path,
or pre-create the auth demo Secrets yourself before using the auth overlay.

## Dependency updates

- Keep upstream services upstream wherever possible.
- When you change chart dependencies, run
  `./hack/helm-dependency-update.sh` so `Chart.lock` and packaged dependency
  archives stay aligned.
- Review upstream release notes and licenses before upgrading dependencies.

## Versioning and publication

- Pushes to `main` publish a unique prerelease version to GHCR.
- Tags in the form `vX.Y.Z` publish the stable `X.Y.Z` version.
- Stable releases should keep `charts/dlh-in-a-box/Chart.yaml` in sync with
  the Git tag used for publication.

## Documentation

- Keep [README.md](README.md) focused on repository context, architecture, and
  navigation.
- Keep [charts/dlh-in-a-box/README.md](charts/dlh-in-a-box/README.md) focused
  on the chart contract and consumer usage.
- Keep [`examples/`](examples/README.md) readable enough to serve as living
  examples, not just test fixtures.
- Every maintained directory should have a local guide file. Use `README.md`
  by default and `_README.txt` inside Helm `templates/` directories.
- Treat genuinely vendored upstream docs as reference material. Prefer
  rewriting the local wrapper docs around them instead of editing vendor docs
  in place.
- If you add or vendor third-party material, update
  [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md),
  [charts/dlh-in-a-box/THIRD_PARTY_NOTICES.md](charts/dlh-in-a-box/THIRD_PARTY_NOTICES.md),
  and any required bundled notice files.

## Ownership

- Repository ownership is managed in `.github/CODEOWNERS`.
- Default code owner is the
  `@sanger-pathogens/data-engineering-and-integration-sanger` team.

## Contribution model

- This repository may be publicly visible, but pull requests are limited to
  repository collaborators.
- External users should not assume that public visibility implies open
  contribution rights.
- Review routing and stewardship live in `.github/CODEOWNERS`.
- Public issue intake is handled through `.github/ISSUE_TEMPLATE/`.

## Pull requests

Good pull requests for this repository usually include:

- a short explanation of the chart-facing change
- documentation or example updates when the supported values surface changes
- note of dependency or license impact, if any
- updates to local directory guides when repository structure changes
