# dlh-in-a-box Chart Guide

This is the main guide for the chart itself.

Audience: people who want to understand what the chart deploys and how to pick
the right install path.

What you will learn: what the chart can deploy, which identity modes it
supports, which values areas matter most, and when to use each example
overlay.

Read next: [../../docs/quickstart.md](../../docs/quickstart.md) for the
simplest first install, or [../../examples/README.md](../../examples/README.md)
if you are choosing between overlays.

## What This Chart Does

This chart installs a group of data-platform tools together as one Helm
release.

Use it when you want one chart to wire the platform pieces together instead of
installing each tool by hand.

Common components in this chart:

| Component | Plain meaning |
| --- | --- |
| `Trino` | The SQL engine people query. |
| `Hive Metastore` | The place where table metadata is stored. |
| `Keycloak` | The login system used by the shared examples. |
| `Ranger` | The system that stores access rules. |
| `Prefect` | The workflow UI and worker components. |
| `CloudBeaver` | A browser-based SQL tool. |
| `DataHub` | An optional metadata catalog. |
| `JupyterHub` | An optional notebook service. |
| `MinIO` | Object storage for local and simple installs. |
| `Vault` | Optional secrets tooling. |

You can enable only the pieces you need.

## Supported Identity Modes

There are two main ways this chart can handle users:

| Mode | Simple meaning |
| --- | --- |
| `externalLdap` | Keycloak handles browser login, but users and groups come from LDAP or Active Directory. This is the shared-environment model used by the dev and prod examples. |
| `keycloakLocal` | Keycloak stores users itself. This is the self-contained local auth model used by `values-local-auth.yaml`. |

## Default Architecture

The shared development and production examples in this repository use this
general model:

- Keycloak handles browser login.
- LDAP or Active Directory supplies users and groups.
- Ranger stores access rules.
- `platformHome` is the optional landing page people see in the browser.
- Prefect and CloudBeaver sit behind browser auth proxies.
- Trino is the main SQL engine.

The auth-enabled local example uses the simpler `keycloakLocal` mode instead.

One important detail:

Trino does not automatically use the Ranger plugin just because Ranger is
enabled elsewhere in the chart. Trino only switches to that plugin when
`global.authorization.ranger.trino.enabled=true` and the Trino image supports
that plugin.

## Start With These Docs

- brand new to the repo:
  [../../docs/prerequisites.md](../../docs/prerequisites.md)
- want the simplest install first:
  [../../docs/quickstart.md](../../docs/quickstart.md)
- want help choosing an example overlay:
  [../../examples/README.md](../../examples/README.md)
- want the access model:
  [../../docs/auth-architecture.md](../../docs/auth-architecture.md)
- want the governed data rules:
  [../../docs/data-governance.md](../../docs/data-governance.md)
- want an optional word list:
  [../../docs/glossary.md](../../docs/glossary.md)

## Choose An Install Path

| Path | Plain-English label | Use this when |
| --- | --- | --- |
| `examples/values-local.yaml` | Simplest local install | You want the easiest manual first install. |
| `make smoke-install` with `examples/values-local-auth.yaml` | Auth-enabled smoke test | You want a local path that also exercises login, browser proxies, and Ranger. |
| `examples/values-dev.yaml` | Shared development example | You want the main LDAP-backed development baseline. |
| `examples/values-prod.yaml` | Production-shaped example | You want the main LDAP-backed production baseline. |
| `examples/values-shared-auth.yaml` | Shared environment with external OIDC provider | You already have an external OIDC provider and do not want bundled Keycloak. |

## Values You Will Touch Most Often

If you are new, these are the main values areas to know:

| Values path | Simple meaning |
| --- | --- |
| `global.identity` | Login settings |
| `global.authorization` | Access and role settings |
| `global.dataCatalogs` | Data source definitions |
| `platformHome` | Browser home page settings |
| `cloudbeaver` | CloudBeaver settings |
| `prefect` | Prefect settings |
| `jupyterhub` | JupyterHub settings |
| `keycloak` | Bundled Keycloak deployment settings |

## Governance And Policy

For shared development and production environments, the chart expects extra
metadata for non-local datasets.

In simple terms, it wants to know:

- what kind of data this is
- how sensitive it is
- whether it contains identifying information
- who owns it
- who looks after it
- which approval record allows it to be used

The chart can check that those fields exist and that the access rules are not
obviously unsafe.

The chart cannot decide whether your organization should approve a dataset in
the first place.

## Platform Roles And Exceptions

The chart uses platform roles as the normal long-term access model.

In plain language, a platform role is a named bundle of access.

Use platform roles for:

- normal team access
- normal app access
- normal long-term permissions

If one person needs extra access for a short time, use an exception role
instead of changing the normal role for everyone.

## Browser Apps And Access Paths

The chart can expose browser apps such as:

- `platformHome`
- `Prefect`
- `CloudBeaver`
- `JupyterHub`

These can share the same sign-in story.

For CloudBeaver, remember:

- browser sign-in goes through the auth proxy
- the saved datasource can be pre-created by admins
- that datasource may use a shared service account
- the chart does not assume every CloudBeaver user types an LDAP password into
  Trino directly

For Prefect, the recommended pattern is to keep the auth proxy in front of it.

## Keycloak Local Users Mode

Use `keycloakLocal` when you want Keycloak to store users itself.

That usually means:

- no LDAP connection
- no Ranger usersync
- a more self-contained setup

The main example for that mode in this repository is:

- [`../../examples/values-local-auth.yaml`](../../examples/values-local-auth.yaml)

## Portal Branding, Icons, And Health

`platformHome` is the optional browser home page.

The most common settings are:

| Values path | Simple meaning |
| --- | --- |
| `platformHome.branding.title` | Main title on the page |
| `platformHome.branding.subtitle` | Smaller text under the title |
| `platformHome.branding.logoUrl` | Logo image |
| `platformHome.branding.faviconUrl` | Browser tab icon |
| `platformHome.theme.*` | Colors and fonts |
| `platformHome.health.enabled` | Turn on built-in health checks for the UI |

## CloudBeaver Seeded Datasources And Trust Material

CloudBeaver can be set up so admins pre-create the connection information for
users.

The most important settings are:

| Values path | Simple meaning |
| --- | --- |
| `cloudbeaver.bootstrap.workspaceSeedExistingSecret` | Secret with saved connection data |
| `cloudbeaver.trustedCa.*` | TLS trust settings for secure database connections |

## LDAPS And Trust Material

If you use secure LDAP, the chart needs certificate trust settings so services
know which LDAP certificate to trust.

Main values:

- `global.identity.directory.ldap.trustedCaExistingSecret`
- `keycloak.trustedCertsExistingSecret`

## Keycloak Client Secret Settings

When Keycloak creates OIDC clients, it reads secret values from one Kubernetes
Secret.

The main setting is:

- `global.identity.provider.keycloak.configCliEnvExistingSecret`

Default name:

- `dlh-keycloak-config-cli-env`

## Example Overlays

- `examples/values-local.yaml`
  simplest manual local install
- `examples/values-local-auth.yaml`
  auth-enabled smoke path that expects demo Secrets
- `examples/values-dev.yaml`
  shared development example
- `examples/values-prod.yaml`
  shared production-shaped example
- `examples/values-shared-auth.yaml`
  shared example using an external OIDC provider

## Reference-Only Material

Some docs under `charts/dlh-in-a-box/charts/` come from upstream projects.

Those are reference docs, not the main starting point for this chart.

## Validation

From the repository root:

```bash
./hack/helm-dependency-update.sh
SKIP_MERMAID_CHECK=1 ./hack/docs-check.sh
./hack/lint.sh
./hack/template.sh
./hack/package.sh
make smoke-install
```

`make smoke-install` is the normal way to exercise
`examples/values-local-auth.yaml`, because the smoke script seeds the demo
Secrets that overlay expects.
