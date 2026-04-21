# Identity And Access Architecture

This guide explains how login and access work in the chart.

Audience: readers who need to understand sign-in, group mapping, browser app
access, and Trino access.

What you will learn: the default shared-environment access model, the local
auth model, what happens in Trino and browser apps, and what the chart checks
for you.

Read next: [../examples/README.md](../examples/README.md) for the overlay map,
or [data-governance.md](data-governance.md) for governed data rules.

## Supported Identity Modes

There are two main ways the chart can handle users:

| Mode | Simple meaning |
| --- | --- |
| `externalLdap` | Users sign in through Keycloak, but the real user list and groups come from LDAP or Active Directory. This is the shared dev and prod model in this repository. |
| `keycloakLocal` | Keycloak stores users itself. This is the local auth model used by `examples/values-local-auth.yaml`. |

## Default Model

The shared development and production examples in this repository use
`externalLdap`.

What that means in plain language:

1. A person opens a browser app such as `platformHome`, Prefect, CloudBeaver,
   or the Trino UI.
2. The browser sends that person to Keycloak to sign in.
3. In shared environments, Keycloak and Ranger usersync read users and groups
   from LDAP or Active Directory.
4. The browser app decides whether the signed-in person may open it.
5. Trino decides whether the signed-in person may query a catalog, schema, or
   table.

Use this table as the simple reference:

| Workload | Authentication source | Authorization source | What the operator must supply |
| --- | --- | --- | --- |
| `platformHome` | Browser login through Keycloak | App group membership and platform role mapping | Keycloak client settings and the right groups or roles |
| `Prefect` | `oauth2-proxy` in front of Prefect, backed by Keycloak | `oauth2-proxy` allowed groups | Prefect proxy client settings and the groups allowed to reach the UI |
| `CloudBeaver` | `oauth2-proxy` in front of CloudBeaver, backed by Keycloak | `oauth2-proxy` allowed groups for the UI, plus any seeded datasource rules behind it | CloudBeaver proxy client settings and, if desired, a seeded datasource secret |
| `Trino` | OIDC for browser and token flows, plus optional LDAP password auth in `externalLdap` mode | Generated Trino rules by default, or Ranger plugin rules only when `global.authorization.ranger.trino.enabled=true` and the image supports the plugin | Trino client settings, user or group alignment, and any Ranger Trino plugin support |

## Keycloak Local Users Model

`keycloakLocal` means Keycloak stores the users itself.

Use this when you do not want to connect to LDAP or Active Directory.

That mode is shown in `examples/values-local-auth.yaml`.

In this mode:

- users are created in Keycloak
- self-registration can be turned on
- Ranger usersync stays off
- the LDAP-focused admin page in `platformHome` stays hidden

## Development Versus Production

Here is how the example files in this repository map to login modes:

| File | What it is for | Identity mode |
| --- | --- | --- |
| `examples/values-local.yaml` | Simplest local install | No shared identity setup |
| `examples/values-local-auth.yaml` | Local auth test | `keycloakLocal` |
| `examples/values-dev.yaml` | Shared dev example | `externalLdap` |
| `examples/values-prod.yaml` | Shared prod-shaped example | `externalLdap` |
| `examples/values-shared-auth.yaml` | Shared example with external OIDC provider | `externalLdap` plus an external OIDC provider |

## Username And Group Alignment

This is the most important rule in the whole auth setup:

all parts of the system need to agree on who the user is.

That means the same person should look the same to:

- Keycloak
- LDAP or Active Directory
- Ranger
- Trino

If those names do not line up, login can work but access can still be wrong.

## Trino

Trino is the tool that actually runs SQL queries.

Keep these three questions separate:

- who is the user
- what groups or roles does the user have
- what data may that user read or change

In this chart:

- shared dev and prod examples use generated Trino rules by default
- Ranger only drives Trino when
  `global.authorization.ranger.trino.enabled=true` and the Trino image
  supports the Ranger plugin
- long-lived access should normally be modeled through
  `global.authorization.platformRoles`

In `externalLdap` mode, Trino can be reached through browser login, token-based
clients, and optional LDAP password auth when that path is enabled.

In `keycloakLocal` mode, the normal user path is token-based rather than LDAP
password-based.

## Platform Roles And Direct-User Exceptions

The chart has a concept called a platform role.

In simple terms, a platform role is a named bundle of access.

Use platform roles for the normal, long-term access model.

If one person needs temporary extra access, use an exception role instead of
changing the normal baseline role for everyone.

## Browser Apps And Admin Surfaces

Several browser apps can share the same login story:

- `platformHome`
  Optional browser home page
- `Prefect`
  Browser workflow UI
- `CloudBeaver`
  Browser SQL UI
- `JupyterHub`
  Optional notebook UI

CloudBeaver needs one extra note:

- browser login goes through the auth proxy and Keycloak
- the saved database connection can be pre-seeded by admins
- that saved connection might use a shared service account
- the chart does not assume every CloudBeaver user types an LDAP password into
  Trino directly

## Prefect

Prefect is put behind `oauth2-proxy` so it can use the same login system as
the rest of the platform.

That means:

- the browser sign-in goes through Keycloak
- group-based access checks happen at the proxy
- optional machine-token access can also be enabled if needed

## Browser URLs Versus In-Cluster URLs

The chart often needs two kinds of URLs:

- a browser URL that a human can open
- an internal cluster URL that one service uses to talk to another service

Those are not always the same thing.

If those two URLs are mixed up, login callbacks and service-to-service calls
can break in confusing ways.

## LDAPS Trust Material

If you use secure LDAP, the chart needs certificate trust settings so the
services know which LDAP certificate to trust.

The main values involved are:

- `global.identity.directory.ldap.trustedCaExistingSecret`
- `keycloak.trustedCertsExistingSecret`

## What The Chart Enforces

The chart checks some things for you:

- required identity settings are present
- incompatible auth modes are rejected
- Prefect auth proxy settings line up
- governed datasets carry the required metadata

## What Operators Still Need To Do

The chart does not do everything for you.

You still need to:

- create the real Secrets
- choose the real usernames and groups
- connect to the real LDAP or Active Directory system if you use one
- test real sign-in and real access in a cluster

## Related Docs

- [glossary.md](glossary.md)
- [data-governance.md](data-governance.md)
- [../examples/README.md](../examples/README.md)
