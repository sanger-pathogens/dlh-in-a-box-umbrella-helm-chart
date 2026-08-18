---
name: release-agent
description: Use when creating tagged Helm chart releases, GitHub Releases, GHCR chart publications, Zenodo citation metadata, DOI records, release notes, and DOI badges for this repository.
---

# Release Agent Skill

Use this skill when an agent or maintainer needs to create a tagged Helm chart
release, publish it through GitHub Actions, create or update the GitHub
Release, and keep Zenodo citation metadata and DOI badges aligned.

This skill is intentionally agent-neutral. It assumes repository, git, GitHub,
and shell access, but it does not require a specific assistant runtime.

## Scope

This workflow covers:

- patch, minor, and major chart releases
- `charts/dlh-in-a-box/Chart.yaml` version bumps
- local Helm validation
- annotated git tags
- GitHub Releases
- GHCR chart publication through the existing workflow
- Zenodo metadata, DOI creation, and DOI badges

It does not cover:

- changing chart runtime behavior
- manually uploading artifacts to Zenodo
- manually publishing Helm packages outside the existing workflow

## Release Rules

- Stable release tags must use `vX.Y.Z`.
- `charts/dlh-in-a-box/Chart.yaml` `version` must equal `X.Y.Z`.
- `appVersion` should usually match `version` for chart-only releases.
- The `helm-publish` workflow rejects a tag if the tag version does not match
  `Chart.yaml`.
- `main` publishes prerelease-style chart versions with run metadata; tags
  publish stable chart versions.
- Keep release commits small and easy to audit.
- If a follow-up hardening commit is not part of the tagged artifact, say so
  explicitly in release notes.

## Preflight

Start from a clean and current `main`:

```bash
git status --short --branch
git fetch --tags origin
git status --short --branch
git tag --list 'v*' --sort=v:refname | tail
```

If the worktree is dirty, inspect changes before editing. Do not revert changes
you did not make.

Confirm the target version and tag do not already exist:

```bash
git tag --list 'v0.5.0'
```

## Metadata Files

For DOI-backed releases, keep both files present and current:

- `.zenodo.json`
- `CITATION.cff`

Update their `version` fields to the release version when creating a new
citable release.

Validate them locally:

```bash
ruby -rjson -e 'JSON.parse(File.read(".zenodo.json")); puts ".zenodo.json OK"'
ruby -rdate -ryaml -e 'YAML.safe_load(File.read("CITATION.cff"), permitted_classes: [Date]); puts "CITATION.cff YAML OK"'
```

## Version Bump

Update `charts/dlh-in-a-box/Chart.yaml`:

```yaml
version: 0.5.0
appVersion: "0.5.0"
```

Search for stale version references:

```bash
rg -n '0\.4\.0|v0\.4\.0' .
```

Only update references that should move with the release. Do not rewrite old
release history or changelog text unless that is the explicit task.

## Local Validation

Use the same Helm version as CI when possible. CI currently uses Helm `v3.12.0`.

Run:

```bash
rm -rf dist
make verify
```

Expected package path:

```text
dist/dlh-in-a-box-X.Y.Z.tgz
```

If local Helm fails with a Docker credential helper error such as
`docker-credential-desktop` missing, retry with a clean temporary Helm registry
and Docker config rather than changing repository files:

```bash
tmp="$(mktemp -d)"
mkdir -p "${tmp}/docker" "${tmp}/registry"
printf '{}' > "${tmp}/registry/config.json"
DOCKER_CONFIG="${tmp}/docker" \
HELM_REGISTRY_CONFIG="${tmp}/registry/config.json" \
./scripts/helm-dependency-update.sh
```

If `test/render-contract.sh` fails because a render-contract expected message drifted,
compare the actual template failure with the corresponding validation template.
Update the contract only when the chart behavior is already correct and the
test expectation is stale.

## Commit And Tag

Commit the release source changes:

```bash
git add charts/dlh-in-a-box/Chart.yaml .zenodo.json CITATION.cff
git commit -m "Release chart vX.Y.Z with citation metadata"
```

Create an annotated tag:

```bash
git tag -a vX.Y.Z -m "Release dlh-in-a-box chart vX.Y.Z" HEAD
```

Push the branch and tag atomically:

```bash
git push --atomic origin main vX.Y.Z
```

Confirm the tag points to the intended commit:

```bash
git ls-remote --tags origin 'vX.Y.Z^{}'
```

## GitHub Release

Create a GitHub Release for every release tag. A git tag alone is not enough.

Use the GitHub UI, `gh release create`, an installed GitHub connector, or the
GitHub REST API. If using REST from a local shell, retrieve credentials without
printing tokens:

```bash
printf 'protocol=https\nhost=github.com\n\n' | git credential fill
```

Do not echo or log the password/token.

Release notes should include:

- short overview
- exact release commit
- chart version and app version
- user-visible changes
- local validation commands
- Helm install snippet
- GitHub Actions verification links after workflows complete
- Zenodo DOI information after Zenodo mints it

Install snippet:

```bash
helm upgrade --install dlh oci://ghcr.io/sanger-pathogens/charts/dlh-in-a-box \
  --version X.Y.Z \
  -n data-lakehouse \
  --create-namespace \
  -f my-values.yaml
```

## Watch CI

After pushing, watch:

- `helm-lint`
- `helm-publish` on `main`
- `helm-publish` on `vX.Y.Z`

The tag publish run is the stable chart publication gate. It should complete:

- dependency update
- lint and license checks
- package chart
- GHCR login
- push chart to GHCR

The workflow links are available under:

- https://github.com/sanger-pathogens/dlh-in-a-box-umbrella-helm-chart/actions/workflows/helm-lint.yaml
- https://github.com/sanger-pathogens/dlh-in-a-box-umbrella-helm-chart/actions/workflows/helm-publish.yaml

If `Update dependencies` fails transiently, rerun or inspect whether the retry
wrapper in `scripts/helm/helm-dependency-update.sh` needs adjustment.

## GHCR Notes

Publication proof comes from the `helm-publish` workflow success.

Anonymous local `helm show chart` may return `401 Unauthorized` depending on
GHCR package visibility or local credentials. Do not claim anonymous install
works unless it has been tested from a clean environment.

## Zenodo DOI Workflow

Zenodo only archives GitHub releases after the repository is enabled in the
Zenodo GitHub settings.

For DOI-backed releases:

1. Ensure the repository is enabled in Zenodo.
2. Commit `.zenodo.json` and `CITATION.cff`.
3. Push the `vX.Y.Z` tag.
4. Create the GitHub Release.
5. Wait for Zenodo to archive the release.
6. Look up the record and DOI.
7. Update the GitHub Release notes and README badge.

Check Zenodo badge resolution by repository ID:

```bash
curl -sSIL https://zenodo.org/badge/latestdoi/1183259546
```

Check for the current record:

```bash
curl -fsSL 'https://zenodo.org/api/records?q=%22dlh-in-a-box%20Umbrella%20Helm%20Chart%22&size=10&sort=mostrecent'
```

For the `v0.4.1` release, Zenodo minted:

- version DOI: `10.5281/zenodo.20731685`
- concept DOI: `10.5281/zenodo.20731684`
- record: https://zenodo.org/records/20731685

## DOI Badge

Use the version DOI badge for a specific release:

```markdown
[![DOI](https://zenodo.org/badge/DOI/10.5281%2Fzenodo.20731685.svg)](https://doi.org/10.5281/zenodo.20731685)
```

Important: URL-encode the slash in the SVG URL as `%2F`. Without that,
GitHub may render a broken image even when Zenodo serves the badge directly.

Add the badge to:

- the GitHub Release notes for the DOI-backed release
- the top badge block in `README.md`

Run:

```bash
SKIP_MERMAID_CHECK=1 ./scripts/docs-check.sh
```

Then commit and push the README badge update.

## If Zenodo Does Not Mint A DOI

If the release existed before Zenodo was enabled, Zenodo may not archive it
retroactively.

Preferred recovery order:

1. Wait a few minutes and press `Sync now` in Zenodo's GitHub settings.
2. Check the repository row and any release error panel in Zenodo.
3. Delete and recreate only the GitHub Release object for the same tag if the
   tag should remain the citable version.
4. If that still does not trigger archival, create the next patch release with
   no runtime changes, for example `v0.4.2`, after confirming metadata is in
   place.

Do not move an existing published tag unless the repository owner explicitly
requests it.

## Final Summary Checklist

When reporting back, include:

- commits created
- tags pushed
- GitHub Release URLs
- workflow URLs and outcomes
- GHCR chart version
- Zenodo record URL
- version DOI and concept DOI
- archive filename, size, and checksum if available
- any caveat about GHCR authentication or in-progress README-only workflows
