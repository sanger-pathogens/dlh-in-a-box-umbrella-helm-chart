# Glossary

This glossary explains the core terms used across the chart and consumer
documentation.

## Core Platform Terms

- `Lakehouse`
  The combined platform made up of object storage, metadata, SQL access,
  orchestration, and optional BI or metadata services.
- `Catalog`
  A named Trino data source such as `redcap` or `bronze`. In this chart, each
  catalog can generate Trino and Hive resources.
- `Consumer overlay`
  An environment-specific values file in a downstream repository that consumes
  this chart.

## Identity And Access Terms

- `OIDC`
  OpenID Connect. This is the browser login protocol used by Keycloak and the
  applications that trust it.
- `Keycloak`
  The default OIDC provider in the documented platform model.
- `LDAP`
  Lightweight Directory Access Protocol. In this project it is the interface
  used to read users and groups from OpenLDAP or Active Directory.
- `Active Directory`
  Microsoft’s directory service. In this project it is treated as an LDAP/LDAPS
  directory plus a source of institutional users and groups.
- `LDAPS`
  LDAP over TLS. This is the production-style way the platform talks to Active
  Directory or another secured LDAP service.
- `Principal`
  The user identity that reaches Trino or another application after login.
- `Group alignment`
  The requirement that the identity seen by Keycloak, LDAP/AD, and Ranger all
  refer to the same human user.

## Authorization Terms

- `Ranger`
  Apache Ranger. In this project it is the Trino authorization surface for
  catalog, schema, table, column, masking, and row-filter policies.
- `authorizedGroups`
  Coarse catalog-level access lists still accepted by the chart. These are now
  migration input, not the end state for sensitive datasets.
- `bootstrapPolicies`
  The chart-owned Ranger policy payload applied during install or upgrade.
- `Platform role`
  A Git-managed access bundle declared under
  `global.authorization.platformRoles`. A platform role can map directory
  groups, direct users, and nested roles to one Ranger role name.
- `Exception role`
  A time-bounded Ranger role used for additive direct-user access outside the
  long-lived Git baseline. Exception roles must carry approval metadata and an
  expiry date.
- `Fine-grained policy`
  A Ranger policy that does more than allow or deny a whole catalog. Examples:
  column masking and row filtering.

## Governance Terms

- `Governance metadata`
  The required `global.dataCatalogs.*.governance` block that classifies a
  dataset and ties it to an approval path.
- `Classification`
  The sensitivity tier for a dataset, such as `restricted-identifiable` or
  `public`.
- `Data steward`
  The person or team responsible for the operational handling of a dataset.
- `Owner PI`
  The principal investigator or equivalent accountable owner for the dataset.
- `Approval reference`
  The human-governance record showing why the dataset is allowed to exist in
  the platform in its current form.

## Application Terms

- `platformHome`
  The lightweight browser launchpad that becomes the default entrypoint for
  human users in the current model.
- `CloudBeaver`
  Browser SQL client. In this chart it is protected by `oauth2-proxy` for
  browser access, but it still connects to Trino with the user’s LDAP or AD
  username and password.
- `Prefect auth proxy`
  `oauth2-proxy` placed in front of Prefect so Keycloak can be the login
  system even though Prefect OSS does not provide the same native auth model as
  the other applications.
- `Bundled component`
  A dependency this chart can deploy directly, such as Keycloak or OpenLDAP.
- `Reference-only doc`
  Documentation kept for context, but not part of the main onboarding path.
