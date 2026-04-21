# Example Overlays

This folder contains example values files.

If you are new, think of an overlay as an example config file you can learn
from or start from.

Audience: people choosing a starting values file.

What you will learn: which overlay is the easiest first path, which ones are
for shared environments, and which files are special-case examples.

Read next: [../docs/quickstart.md](../docs/quickstart.md) for the recommended
first install, or [../docs/auth-architecture.md](../docs/auth-architecture.md)
if you are choosing an auth model.

## Overlay selection

Choose the first matching row:

| Plain-English label | File | Use this when |
| --- | --- | --- |
| Simplest local install | `values-local.yaml` | You want the easiest manual first install. |
| Auth-enabled smoke test | `values-local-auth.yaml` | You want a local path that also exercises login and access pieces. |
| Shared development example | `values-dev.yaml` | You want the main LDAP-backed dev baseline. |
| Production-shaped example | `values-prod.yaml` | You want the main LDAP-backed production baseline. |
| Shared environment with external OIDC provider | `values-shared-auth.yaml` | You already have an external OIDC provider and do not want bundled Keycloak. |

## Overlay inventory

| File | Plain-English label | What it is for |
| --- | --- | --- |
| `values-local.yaml` | Simplest local install | The recommended first manual install. |
| `values-local-auth.yaml` | Auth-enabled smoke test | Local install with Keycloak, Ranger, browser proxies, and seeded demo secrets. |
| `values-local-superset.yaml` | Local Superset example | Local install focused on Superset. |
| `values-local-layers.yaml` | Richer local layout | Local install that shows more layering and structure. |
| `values-dev.yaml` | Shared development example | Main shared development baseline. |
| `values-prod.yaml` | Production-shaped example | Main shared production baseline. |
| `values-prod-layers.yaml` | Layered production example | Production-shaped example with more layering. |
| `values-shared-auth.yaml` | Shared environment with external OIDC provider | Shared example that expects an external OIDC provider. |
| `values-external-s3.yaml` | External S3 example | Example that points at external object storage. |
| `values-minio.yaml` | MinIO-focused example | Example focused on MinIO setup. |

## Validation expectations

- every file in this folder is part of the repo’s validation story
- `./hack/lint.sh` checks them
- `./hack/template.sh` renders them

Important difference between the two main local examples:

- `values-local.yaml`
  is the easiest manual local install
- `values-local-auth.yaml`
  is the auth-enabled smoke path and is normally run through
  `make smoke-install` because that script creates the demo Secrets it needs

## Shared-Environment Expectations

The shared examples are not self-contained.

They expect real environment-specific things such as:

- real hostnames
- real TLS Secrets
- real LDAP credentials
- real OIDC client secrets
- real storage credentials

## Governance Expectation

For non-local datasets, the examples should include a `governance` block under
`global.dataCatalogs.<catalog>.governance`.

## Security note

- local examples may contain demo credentials
- non-local examples should not contain real secrets
- external storage examples should point to existing Secrets instead of
  committing credentials into Git

## Maintainer note

Keep these files readable. They are not just test inputs. They are also part of
the user documentation.
