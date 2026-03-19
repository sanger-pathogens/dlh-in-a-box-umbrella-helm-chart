# Contributing

Thanks for contributing to `dlh-in-a-box`.

This repository is intentionally focused on one thing: publishing a reusable
umbrella Helm chart for a Kubernetes-based lakehouse control plane. Changes
should keep that scope tight and avoid turning this repo into the home for
pipeline code, Spark jobs, or environment-specific application logic.

## Local workflow

Before opening a pull request, run the standard local checks:

```bash
./hack/helm-dependency-update.sh
./hack/lint.sh
./hack/template.sh
./hack/package.sh
```

If you prefer a shorter entry point, the repository root `Makefile` exposes the
same common tasks:

```bash
make deps
make lint
make template
make package
```

`./hack/lint.sh` and `./hack/template.sh` exercise every tracked example values
file under `examples/` by default, so the examples directory should be treated
as part of the supported surface rather than a dumping ground for stale notes.

If you are validating the full local deployment path, use:

```bash
helm upgrade --install dlh charts/dlh-in-a-box \
  -n data-lakehouse-local \
  --create-namespace \
  -f examples/values-local.yaml
```

## Dependency updates

- Keep upstream services upstream wherever possible.
- When updating `Chart.yaml` dependencies, run `./hack/helm-dependency-update.sh`
  so `Chart.lock` and the local packaged dependencies stay aligned.
- Review upstream release notes and licenses before upgrading dependencies.

## Versioning and publication

- Pushes to `main` publish a unique prerelease chart version to GHCR.
- Tags in the form `vX.Y.Z` publish the stable `X.Y.Z` chart version.
- Stable releases should keep `charts/dlh-in-a-box/Chart.yaml` in sync with the
  Git tag used for publication.

## Documentation

- Keep the root `README.md` focused on architecture, repository navigation, and
  handover for new maintainers.
- Keep `charts/dlh-in-a-box/README.md` focused on chart consumers and the chart
  values surface.
- Every maintained directory should carry a local guide file. Use `README.md`
  by default. In Helm `templates/` directories, use `_README.txt` so source
  validation does not try to parse the documentation as manifests. Link new
  guides from the nearest parent README.
- If you add or vendor third-party material, update
  `THIRD_PARTY_NOTICES.md`, `charts/dlh-in-a-box/THIRD_PARTY_NOTICES.md`, and
  any required bundled license files.
- `./hack/docs-check.sh` enforces the directory-guide convention and should stay
  green.

## Ownership

- Repository ownership is managed in `.github/CODEOWNERS`.
- Default code owner is the
  `@sanger-pathogens/data-engineering-and-integration-sanger` team.

## Contribution model

- This repository may be publicly visible, but pull requests are restricted to
  repository collaborators.
- External users should not assume that public visibility implies open
  contribution rights.
- Review routing and ongoing stewardship are handled through
  `.github/CODEOWNERS`.
- Public issue intake is handled through `.github/ISSUE_TEMPLATE/`.

## Pull requests

Good pull requests for this repository usually include:

- a short explanation of the user-facing or operator-facing change
- updates to examples or documentation when the values surface changes
- note of any dependency or license impact
- updates to directory README files when repository structure changes
