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

- Keep the root `README.md` focused on architecture, operations, and
  consumption from other repositories.
- Keep `charts/dlh-in-a-box/README.md` focused on chart consumers.
- If you add or vendor third-party material, update
  `THIRD_PARTY_NOTICES.md`, `charts/dlh-in-a-box/THIRD_PARTY_NOTICES.md`, and
  any required bundled license files.

## Ownership

- Repository ownership is managed in `.github/CODEOWNERS`.
- Default code owners are the
  `@sanger-pathogens/data-engineering-and-integration-sanger` team together
  with `@PsycheShaman` and `@y-popov`.

## Pull requests

Good pull requests for this repository usually include:

- a short explanation of the user-facing or operator-facing change
- updates to examples or documentation when the values surface changes
- note of any dependency or license impact
