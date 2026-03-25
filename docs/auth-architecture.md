# Identity And Access Architecture

This guide explains the default identity and access model for shared
environments.

It is written for chart consumers and maintainers who need to understand how
Keycloak, LDAP/AD, Trino, Ranger, and Prefect fit together.

## Default Model

```mermaid
flowchart LR
  User[User] --> Portal[platformHome]
  Portal --> Keycloak[Keycloak]
  LDAP[OpenLDAP or Active Directory] --> Keycloak
  LDAP --> RangerUsersync[Ranger usersync]
  Keycloak --> Trino[Trino]
  Keycloak --> Superset[Superset]
  Keycloak --> DataHub[DataHub]
  Keycloak --> PrefectProxy[Prefect oauth2-proxy]
  PrefectProxy --> Prefect[Prefect]
  Keycloak --> CloudBeaverProxy[CloudBeaver oauth2-proxy]
  CloudBeaverProxy --> CloudBeaver[CloudBeaver]
  RangerUsersync --> Ranger[Apache Ranger]
  Ranger --> Trino
```

In plain English:

- Keycloak handles browser login.
- LDAP or AD remains the source of users and groups.
- Platform roles provide the Git-managed abstraction between directory subjects
  and Ranger policies.
- `platformHome` is the browser launchpad, not an iframe container.
- Ranger holds the Trino data-access rules.
- Prefect and CloudBeaver are protected at the front door by `oauth2-proxy`.

## Why Keycloak Is The Default

Keycloak gives the platform one OIDC issuer across Trino, Superset, DataHub,
and Prefect access. That means the institution does not need a separate OIDC
product just to make the platform work.

If an institution already has another preferred OIDC provider, the chart can
still use it. That path remains supported, but it is no longer the primary
documented architecture.

## Development Versus Production

| Environment | Identity source | Group source | Notes |
| --- | --- | --- | --- |
| Development | Bundled Keycloak | Bundled OpenLDAP | Useful for proving the full login and group flow end to end |
| Production | Bundled Keycloak | External AD/LDAP over LDAPS | Matches the institutional source of truth while keeping one platform OIDC issuer |

## Username And Group Alignment

The most important rule in this design is identity alignment.

The following must all refer to the same person:

- the principal inside the OIDC token
- the username used for LDAP or AD lookup
- the subject Ranger policies evaluate

If those identifiers drift apart, users can log in successfully but receive
the wrong groups or no groups at all.

## Trino

```mermaid
flowchart TD
  BrowserLogin[Browser login via OIDC] --> Principal[Principal]
  Principal --> LdapPassword[Optional LDAP password auth]
  Principal --> GroupLookup[LDAP or AD group lookup]
  GroupLookup --> RangerUsersync[Ranger usersync]
  RangerUsersync --> RangerRoles[Ranger platform roles]
  RangerRoles --> Ranger[Ranger]
  Ranger --> Decision[Catalog, schema, table, column, mask, row-filter decisions]
```

The chart now treats Ranger as the steady-state Trino authorization layer.

- `authorizedGroups` is now migration-only input. Use it only when
  `global.authorization.ranger.importCatalogAcls=true`.
- Long-lived data-access bundles should be declared under
  `global.authorization.platformRoles`.
- Sensitive datasets should add explicit Ranger bootstrap policies for masking
  and row filtering, and those policies should normally target Ranger roles
  rather than raw groups or users.
- When Trino uses LDAP password auth against LDAPS, the chart expects trusted
  CA material so certificate validation is real.

That mixed-auth Trino path is deliberate. Browser SSO does not replace the
LDAP password path used by Python, R, JDBC, DBeaver, or CloudBeaver query
sessions.

## Platform Roles And Direct-User Exceptions

The steady-state pattern is:

- LDAP or AD remains the source of institutional groups.
- `global.authorization.platformRoles` maps those directory groups, selected
  direct users, and nested role bundles into Ranger roles.
- Ranger policies then target those roles.

Direct-user grants are still allowed, but only as exceptions:

- use short-lived exception roles with names like
  `exception-redcap-readonly-analyst-am83-20261231`
- store approval metadata and expiry inside the Ranger role description
- keep the exception additive by nesting it into the base platform role

The chart also ships an exception-role audit job so undocumented or expired
exception roles can be flagged and cleaned up.

## Superset

Superset uses the same OIDC issuer as the rest of the platform.

The important operational rule is that Superset should query Trino as the
logged-in user or via impersonation patterns that preserve the real user
identity. Otherwise Ranger policies cannot reflect the person actually using a
dashboard or SQL Lab.

## DataHub

DataHub also trusts the same OIDC issuer.

DataHub is a metadata and policy-discovery layer. In this design, it is not the
enforcement source for SQL authorization. Ranger is.

## Prefect

```mermaid
flowchart LR
  User[User] --> Proxy[oauth2-proxy]
  Proxy --> Keycloak[Keycloak]
  Proxy --> Prefect[Prefect]
```

Self-hosted Prefect OSS does not provide the same native SSO and RBAC story as
the other components. The recommended pattern is:

- put `oauth2-proxy` in front of Prefect
- redirect login to Keycloak
- allow access based on groups such as `dlh-app-prefect`

If you want a branded login page, customize the Keycloak theme and set
`global.identity.provider.keycloak.loginTheme`. Do not build a custom Prefect login
page.

## Browser Entry And CloudBeaver

```mermaid
flowchart LR
  Browser[Browser] --> Portal[platformHome]
  Portal --> Keycloak[Keycloak]
  Portal --> Superset[Superset]
  Portal --> DataHub[DataHub]
  Portal --> Trino[Trino UI]
  Portal --> PrefectProxy[Prefect oauth2-proxy]
  Portal --> CloudBeaverProxy[CloudBeaver oauth2-proxy]
  CloudBeaverProxy --> CloudBeaver[CloudBeaver]
  CloudBeaver --> TrinoPassword[Trino LDAP password auth]
  TrinoPassword --> Ranger[Ranger]
```

The launchpad hides links using Keycloak group claims such as:

- `dlh-app-superset`
- `dlh-app-datahub`
- `dlh-app-trino`
- `dlh-app-prefect`
- `dlh-app-cloudbeaver`

The launchpad is not the security boundary. The app or Trino itself still
enforces the real access decision.

Platform administrators also get an Access Admin section in the portal. It is a
read-only map of:

- the Git-managed platform roles
- their directory group mappings
- their app entitlements
- any declared direct-user exception grants

That section links to Ranger Admin when
`global.authorization.ranger.admin.browserUrl` is configured. Ranger Admin is
the first writable UI for data-access exceptions; it does not replace the Git
baseline.

## LDAPS Trust Material

When the directory URL starts with `ldaps://` and `allowInsecure=false`, the
chart expects CA material so all components validate the same directory
certificate chain.

```mermaid
flowchart LR
  CA[LDAP or AD CA Secret] --> Keycloak
  CA --> Trino
  CA --> RangerUsersync
```

The chart validates the alignment between:

- `global.identity.directory.ldap.trustedCaExistingSecret`
- `keycloak.trustedCertsExistingSecret`
- the Trino and Ranger usersync mounts generated from that same contract

## What The Chart Enforces

- Trino identity settings are internally aligned.
- Prefect proxy values are aligned with the OIDC client contract.
- Non-local datasets must carry governance metadata.
- Restricted datasets must use explicit Ranger policy coverage.
- Restricted-identifiable datasets with direct or quasi identifiers must have
  Ranger fine-grained policy coverage.

## What Operators Still Need To Do

- create the real Kubernetes secrets for OIDC clients, LDAP bind accounts, and
  CA material
- ensure Keycloak, LDAP/AD, and Ranger agree on usernames and groups
- keep app front-door access directory-controlled and use Ranger only for data
  access decisions inside Trino
- decide the real group taxonomy with the institution
- test real login and authorization flows in a cluster

## Related Docs

- [glossary.md](glossary.md)
- [data-governance.md](data-governance.md)
- [../examples/README.md](../examples/README.md)
