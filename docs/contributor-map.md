# Contributor Map

This page explains the repository from a maintainer's point of view.

Audience: internal collaborators and anyone trying to understand where a change
belongs.

What you will learn: which part of the repo owns which kind of behavior, where
to start for common changes, and which validation path matches each change.

Read next: [../CONTRIBUTING.md](../CONTRIBUTING.md) for the workflow rules, or
[../hack/README.md](../hack/README.md) for the local validation scripts.

## Repository Map

Use this mental model:

- `charts/dlh-in-a-box/`
  the chart defaults, schema, templates, and chart-owned wrapper docs
- `examples/`
  supported example overlays that double as living documentation
- `docs/`
  newcomer and maintainer explanations
- `hack/`
  local validation, rendering, packaging, and smoke-install scripts
- `.github/workflows/`
  CI wrappers around the same validation and publish flow

The repository is public to read and reuse, but day-to-day implementation work
and pull requests are mainly for repository collaborators.

## Change X Here

| If you want to change... | Start here |
| --- | --- |
| The default values surface | `charts/dlh-in-a-box/values.yaml` and `charts/dlh-in-a-box/values.schema.json` |
| How the chart renders Kubernetes objects | `charts/dlh-in-a-box/templates/` |
| Which example install paths are documented and tested | `examples/` and `examples/README.md` |
| The newcomer explanation of the repo | `README.md`, `docs/prerequisites.md`, and `docs/quickstart.md` |
| The chart usage guide | `charts/dlh-in-a-box/README.md` |
| Login and access explanations | `docs/auth-architecture.md` |
| Governed data explanations | `docs/data-governance.md` |
| Local validation behavior | `hack/` |
| CI or publish behavior | `.github/workflows/` and `docs/release-playbook.md` |
| Chart dependencies | `charts/dlh-in-a-box/Chart.yaml`, `Chart.lock`, and `./hack/helm-dependency-update.sh` |
| Third-party notices | `THIRD_PARTY_NOTICES.md`, `charts/dlh-in-a-box/THIRD_PARTY_NOTICES.md`, and any bundled notice files |

## Typical Maintainer Loop

1. Make the chart or docs change.
2. Update example overlays if the supported values surface changed.
3. Update the relevant docs in the same change.
4. Run `make lint` and `make template`.
5. Run `make package` when the packaging path matters.
6. Run `make smoke-install` when auth-related local behavior changed.

## Things To Be Careful About

- Do not put real secrets in tracked example files.
- Do not edit packaged dependency archives by hand. Use
  `./hack/helm-dependency-update.sh`.
- Treat vendored upstream docs as reference material. Prefer updating the local
  wrapper docs around them.
- Keep the README, example overlays, local scripts, and workflow docs aligned.
  Newcomers get lost when those drift apart.
