# Spec for Ranger-Keycloak integration

## Mission

We want to make Keycloak to be a centralised Identity Provider.
Keycloak should be a central place to expose users, groups and roles to platform applications.

When LDAP is configured, LDAP is the source of truth for users and groups, and Keycloak federates those users and groups.
When LDAP is not configured, Keycloak local users and groups are the source of truth.

Keycloak is the source of truth for platform roles and platform role membership.

Ranger should receive users, groups and platform roles from the configured identity source path in order to define policies against roles and being able to map users to roles.

User - is a person or a service account.
Group - is a collection of users.
Role - is a collection of permissions.

We need to have 3 human platform roles (besides service roles):
1) platform-admin
2) platform-user
3) platform-viewer

We need to have 3 groups:
1) admins
2) data-analyst
3) principal-investigator

From Keycloak point of view:
1) platform-admin should have access to each component
2) platform-user should have access to superset, datahub, jupyterhub, cloudbeaver
3) platform-viewer should have access to superset, datahub

Access can be granted using client-specific roles such as "prefect:access" or "datahub:access"

From Ranger point of view:
1) platform-admin should have write access
2) platform-user and platform-viewer should have read access

## Technical details

Use Apache Ranger Usersync for users and groups when LDAP is configured.
In LDAP mode, Keycloak and Ranger Usersync should both receive users and groups from the same LDAP server.
When LDAP is not configured, sync users and groups from Keycloak to Ranger using Ranger APIs.

Apache Ranger Usersync cannot sync Keycloak roles, so platform roles and role membership always need a Keycloak-to-Ranger role sync path.

If you need to write a script, use Ranger API, never ingest data directly to Ranger database.


If this helps, you can configure Ranger direct SSO to keycloak instead of oauthproxy. 
Implement this only if this simplify your task, otherwise it will done in the next iteration.

## Road map

Proper configuration of Ranger-Trino access control will be done in the next iteration.
For now we just need to sync users, groups and roles into Ranger using the supported LDAP or Keycloak-local identity source path.

## Current repository structure

There are two separate responsibility boundaries.

### dlh-in-a-box-umbrella-helm-chart

This repository owns the reusable chart contract. The relevant implementation is in:

- `charts/dlh-in-a-box/values.yaml`
- `charts/dlh-in-a-box/values.schema.json`
- `charts/dlh-in-a-box/templates/_helpers.tpl`
- `charts/dlh-in-a-box/templates/identity-validation.yaml`
- `charts/dlh-in-a-box/templates/governance-validation.yaml`
- `charts/dlh-in-a-box/templates/ranger-automation.yaml`
- `charts/dlh-in-a-box/templates/ranger-browser-proxy.yaml`
- `examples/values-dev.yaml`
- `examples/values-prod.yaml`
- `hack/testdata/render-contract`

The chart already has:

- bundled Keycloak support through the Bitnami Keycloak chart and keycloak-config-cli
- configurable OIDC clients for Superset, DataHub, Trino, JupyterHub, CloudBeaver proxy, Prefect proxy, Ranger proxy, MinIO, Vault, Headlamp, and platform-home
- Keycloak group claim emission through the configured groups claim
- `global.authorization.platformRoles`, where each role can define app entitlements, seeded users, directory groups, and Ranger role names
- Ranger bootstrap automation that creates Ranger services, roles, exception roles, and policies through Ranger APIs
- LDAP usersync automation that reads LDAP and calls Ranger APIs
- Keycloak-local usersync automation that reads Keycloak users and calls Ranger APIs for `xusers`, but currently also writes Ranger portal-user records directly through Postgres

Important gap: the chart does not currently have a first-class Keycloak platform role/group catalog. Browser access is mostly expressed as Keycloak groups such as `platform-app-superset` and `platform-role-platform-admin`, while Ranger data authorization is expressed as Ranger roles and policies. The current Keycloak-local sync can project live Ranger role membership back into Keycloak app groups, which is the wrong source-of-truth direction for this mission. The implementation must remove support for Ranger as the source of roles or role membership and make Keycloak the only routine source for platform roles.

### icddrb-data-platform-infra

This repository owns the icddr,b deployment overlays, operational scripts, Vault integration, runbooks, and access documentation. The relevant implementation is in:

- `platform/dlh-in-a-box/values-dev.yaml`
- `platform/dlh-in-a-box/values-prod.yaml`
- `platform/dlh-in-a-box/scripts/sync_keycloak_local_users_to_ranger.sh`
- `platform/dlh-in-a-box/scripts/sync_keycloak_directory_provider.sh`
- `platform/dlh-in-a-box/scripts/formal_validate_dev_platform.sh`
- `docs/concepts/auth-and-access.md`
- `docs/architecture/browser-access-and-sso.md`
- `docs/access/sops`

The infra overlays currently define four main human platform roles:

- `platform-admin`
- `data-analyst`
- `scientist`
- `principal-investigator`

The new mission wants three roles and three groups:

- roles: `platform-admin`, `platform-user`, `platform-viewer`
- groups: `admins`, `data-analyst`, `principal-investigator`

The deployment-specific overlays therefore need to collapse the current analyst/scientist/principal-investigator model into the new role model, and they need to stop treating Ranger as the source of routine role membership.
They should keep supporting LDAP-backed users and groups where LDAP is configured.

Important gap: the infra repo still contains an older shell sync script that directly queries and updates the Ranger database. That script conflicts with the mission constraint: if a script is required, it must use the Ranger API and must not ingest data directly into the Ranger database.

## Target model

The platform has two identity source layers.

Users and groups:

- when LDAP is configured, LDAP is the source of truth for users and groups
- in LDAP mode, Keycloak federates or syncs users and groups from LDAP
- in LDAP mode, Ranger Usersync reads users and groups from the same LDAP server
- when LDAP is not configured, Keycloak local users and groups are the source of truth
- in Keycloak-local mode, Ranger receives users and groups from Keycloak through the chart-managed API sync job

Platform roles and app/data access entitlements:

- Keycloak is always the source of truth for platform roles and platform role membership
- Keycloak roles may be assigned directly to users or inherited through groups
- Ranger receives platform roles and role membership from Keycloak
- Ranger is never the source of truth for users, groups, roles, or role membership

Ranger receives a projection of that identity state:

- LDAP users and groups become Ranger users and groups in LDAP mode
- Keycloak users and groups become Ranger users and groups in Keycloak-local mode
- Keycloak roles become Ranger roles
- Keycloak role membership is converted into Ranger role users and/or groups

Use this initial mapping:

| Keycloak group | Keycloak realm role | Ranger role | Browser app access |
| --- | --- | --- | --- |
| `admins` | `platform-admin` | `platform-admin` | all enabled platform components |
| `data-analyst` | `platform-user` | `platform-user` | Superset, DataHub, JupyterHub, CloudBeaver |
| `principal-investigator` | `platform-viewer` | `platform-viewer` | Superset, DataHub |

The three platform roles are chart-owned built-ins because platform behavior, app access, Ranger role projection, validation, and documentation rely on them.
The chart may allow deployments to override role labels, descriptions, app access details, or Ranger role names, and it may allow additional deployment-specific roles, but the built-in role keys remain part of the chart contract.

The three groups are deployment-owned.
The infra repo supplies the concrete group names and maps them to platform roles.
The chart should not hard-code institutional group names as required defaults.
In LDAP mode, those groups must already exist in LDAP and be federated into Keycloak.
In Keycloak-local mode, the chart may create the infra-supplied groups in Keycloak because Keycloak is the local user/group store.

For app access, use the real Keycloak realm roles and, where a component needs component-scoped authorization, Keycloak client roles such as `prefect:access`, `datahub:access`, or `superset:access`. Do not keep or introduce `platform-app-*` compatibility roles or groups as part of the new model, and do not sync any app-access-only entitlement to Ranger.

For Ranger in this iteration:

- `platform-admin` gets write-level policy membership
- `platform-user` gets read-level policy membership
- `platform-viewer` gets read-level policy membership
- full Ranger-Trino authorization hardening remains for the next iteration, as stated in the road map

## Implementation plan

### 1. Change the chart contract

In `dlh-in-a-box-umbrella-helm-chart`, add a reusable identity-to-authorization catalog under `global.identity` or `global.authorization`. A practical shape is:

```yaml
global:
  identity:
    accessModel:
      enabled: true
      builtInRoles:
        platform-admin:
          enabled: true
          appAccess:
            superset: true
            datahub: true
            jupyterhub: true
            cloudbeaver: true
            prefect: true
            ranger: true
            trinoUi: true
        platform-user:
          enabled: true
          appAccess:
            superset: true
            datahub: true
            jupyterhub: true
            cloudbeaver: true
        platform-viewer:
          enabled: true
          appAccess:
            superset: true
            datahub: true
      additionalRoles: {}
      groupRoleMappings:
        admins:
          roles:
            - platform-admin
        data-analyst:
          roles:
            - platform-user
        principal-investigator:
          roles:
            - platform-viewer
```

The chart should ship built-in defaults for `platform-admin`, `platform-user`, and `platform-viewer`.
The infra repo should supply `groupRoleMappings`.
Examples may use `admins`, `data-analyst`, and `principal-investigator`, but those group names are not chart-owned.

Keep `global.authorization.platformRoles` for Ranger policy compatibility, but make it possible to derive it from the new Keycloak-centered platform role model. Do not remove the old key immediately; use it as the rendered Ranger role projection until all overlays are migrated.

### 2. Extend Keycloak rendering

Update `charts/dlh-in-a-box/values.yaml` keycloak-config-cli realm rendering to create:

- chart-owned realm roles `platform-admin`, `platform-user`, and `platform-viewer`
- any additional deployment-defined realm roles
- infra-supplied Keycloak groups only when Keycloak-local mode is active
- group-to-realm-role mappings using the table above
- client roles per enabled app client where the app needs component-scoped access, with group-to-client-role mappings
- token mappers that expose realm roles and relevant client roles to applications using stable claims

In LDAP mode, the chart should not try to create LDAP groups.
It should map the infra-supplied LDAP group names, as seen in Keycloak after federation, onto the chart-owned platform roles.

Applications should authorize browser access from realm roles or client roles. The implementation should remove reliance on `platform-app-*` groups for Superset, DataHub, JupyterHub, CloudBeaver, and similar browser access checks.

### 3. Support LDAP and Keycloak-local Ranger sync paths

Do not use Apache Ranger Usersync for Keycloak as a primary integration path. Ranger Usersync is suitable for LDAP-style sources, and the current chart already supports an LDAP usersync mode. It does not solve Keycloak role synchronization.

The chart should support two user/group sync paths.

LDAP mode:

- enabled when `global.identity.directory.ldap.enabled=true`
- LDAP is the source of truth for users and groups
- Keycloak receives users and groups from LDAP through the existing Keycloak directory provider configuration
- Ranger Usersync receives users and groups from the same LDAP server
- the Keycloak-to-Ranger role sync still reads Keycloak platform roles and role membership, then creates or updates Ranger roles
- the role sync must not create duplicate Ranger users or groups already supplied by Ranger Usersync

Keycloak-local mode:

- enabled when LDAP is not configured
- Keycloak local users and groups are authoritative
- the chart-managed Keycloak-to-Ranger API sync creates or updates Ranger users, groups, and roles

Add or adapt chart-managed sync jobs in `charts/dlh-in-a-box/templates/ranger-automation.yaml` so they:

- authenticate to Keycloak Admin API
- read enabled users from the configured realm when Keycloak-local mode is active
- read configured groups from Keycloak when Keycloak-local mode is active
- read configured platform roles and role mappings from Keycloak in both LDAP and Keycloak-local modes
- call Ranger APIs to ensure users and groups exist only when Keycloak-local mode is active
- call Ranger role APIs to create or update `platform-admin`, `platform-user`, and `platform-viewer`
- assign Ranger role membership from Keycloak role membership
- ignore Keycloak client roles and app-access-only entitlements when building Ranger state
- optionally prune only objects marked as chart-managed, not arbitrary operator-created Ranger state

The job must use Ranger APIs only. Remove the Postgres dependency from the chart-managed Keycloak-local sync path:

- remove `import psycopg`
- remove `RANGER_POSTGRES_PASSWORD`
- remove `sync_ranger_sql`
- remove the `psycopg[binary]` install in the CronJob command
- stop rendering Ranger Postgres credentials into the local sync job

If Ranger Admin UI visibility requires portal-user records, first verify whether the Ranger API or Ranger Usersync can create the required visible user state. If it cannot, document the limitation and keep the sync API-only rather than writing direct SQL.

### 4. Make Keycloak the only role source

Replace the current role source-of-truth choices with a Keycloak-only role-membership source for this mission:

```yaml
global:
  authorization:
    platformRoleMembershipSource: keycloak
```

Render-time validation should reject `global.authorization.platformRoleMembershipSource=ranger`. Do not implement or retain a mode where Ranger owns platform roles or role membership.

If the chart keeps `git` temporarily for backward compatibility with existing consumers, it must be outside this mission path and must not be used by the icddr,b overlays. The implementation plan for this mission should assume:

- Keycloak owns role definitions and role membership
- Ranger receives only a projection
- LDAP may own users and groups when LDAP is configured
- Keycloak owns users and groups only when LDAP is not configured
- no Ranger-to-Keycloak projection job is rendered
- no portal workflow writes role membership to Ranger as the source of truth

### 5. Update chart validation and examples

Update `identity-validation.yaml`, `governance-validation.yaml`, `values.schema.json`, and render-contract fixtures so the chart validates:

- all infra-supplied groups reference known chart-owned or deployment-added roles
- all roles use supported app keys
- the built-in role keys `platform-admin`, `platform-user`, and `platform-viewer` exist and cannot be deleted from the mission path
- enabled app clients have the required client IDs and secrets
- LDAP mode requires enough LDAP configuration for both Keycloak federation and Ranger Usersync
- Keycloak-local mode disables Ranger Usersync and enables the Keycloak-to-Ranger user/group API sync
- `platformRoleMembershipSource=keycloak` requires bundled Keycloak or a configured Keycloak Admin API endpoint
- `platformRoleMembershipSource=keycloak` requires Ranger to be enabled when Ranger role sync is enabled
- `platformRoleMembershipSource=ranger` fails validation
- `platform-app-*` app-access groups are not generated by the new access model
- Keycloak client roles are not synchronized to Ranger roles unless explicitly declared as platform data roles
- no Keycloak-to-Ranger sync job renders with Postgres credentials

Update examples so they show the three-role/three-group model instead of the older four-role persona model.

### 6. Update icddr,b overlays

In `icddrb-data-platform-infra`, update `platform/dlh-in-a-box/values-dev.yaml` and `platform/dlh-in-a-box/values-prod.yaml`:

- set `global.authorization.platformRoleMembershipSource: keycloak`
- supply the three deployment-owned group names: `admins`, `data-analyst`, `principal-investigator`
- rely on the chart-owned built-in platform roles: `platform-admin`, `platform-user`, `platform-viewer`
- map `admins` to `platform-admin`
- map `data-analyst` to `platform-user`
- map `principal-investigator` to `platform-viewer`
- keep production LDAP settings as the user/group source where LDAP is configured
- keep development Keycloak-local settings as the user/group source where LDAP is not configured
- remove or migrate the current `scientist` role
- replace current `platform-role-data-analyst`, `platform-role-scientist`, and `platform-role-principal-investigator` policy references with the new Ranger roles where appropriate
- remove `platform-app-*` access groups from browser-access configuration and replace them with realm-role or client-role checks
- remove `platform-role-platform-admin` as a browser-access compatibility group unless it remains only as a temporary migration alias outside Ranger sync

For the current REDCap example policies:

- admin write policy should target Ranger role `platform-admin`
- read policies should target Ranger roles `platform-user` and `platform-viewer`
- old group-based policy references should be removed once the Ranger role sync is in place

### 7. Remove direct Ranger database sync from infra

Replace `platform/dlh-in-a-box/scripts/sync_keycloak_local_users_to_ranger.sh` with either:

- a wrapper that invokes the chart-managed Keycloak-to-Ranger sync job, or
- a deployment-specific API-only script that mirrors the chart behavior

The replacement must not:

- run SQL against Ranger Postgres
- read from `x_user`
- write to `x_user`
- read from `x_portal_user`
- write to `x_portal_user`
- write to `x_portal_user_role`

Any validation logic that currently checks those tables should be changed to use Ranger APIs.

### 8. Update operational docs

Update infra docs and SOPs to reflect the new source of truth:

- in LDAP mode, LDAP is where operators create users and manage source group membership
- in Keycloak-local mode, Keycloak Admin is where operators create users and manage source group membership
- Keycloak Admin is where operators assign or inspect platform roles
- Ranger Admin is where operators inspect the projected Ranger roles and policies, not where routine membership starts
- the portal Access Control behavior should either be hidden for this mode or changed to call Keycloak rather than Ranger
- remove language that says Ranger is the role-membership source for normal operation
- remove language that instructs operators to grant application access through `platform-app-*` groups

At minimum update:

- `docs/concepts/auth-and-access.md`
- `docs/architecture/browser-access-and-sso.md`
- `docs/access/sops/assign-directory-users-and-groups-to-platform-roles.md`
- `docs/access/sops/grant-browser-access-in-keycloak.md`
- `docs/access/sops/grant-data-access-in-ranger.md`
- `docs/access/sops/create-or-change-platform-role.md`

### 9. Validate

Chart repository validation:

```bash
./hack/docs-check.sh
./hack/render-contract.sh
./hack/template.sh examples/values-dev.yaml
```

Infra repository validation:

```bash
./scripts/check_docs.sh
CHART_REF=../dlh-in-a-box-umbrella-helm-chart/charts/dlh-in-a-box ./platform/dlh-in-a-box/scripts/check_rendered_manifests.sh
```

Cluster validation after deployment:

- in LDAP mode, choose an LDAP-backed Keycloak user in each mapped group
- in Keycloak-local mode, create or choose a Keycloak-local user in each mapped group
- confirm Keycloak tokens contain the expected realm-role and client-role claims
- confirm Ranger contains users and groups from the configured LDAP or Keycloak-local path
- confirm Ranger contains platform roles and role membership projected from Keycloak
- confirm Ranger does not contain `platform-app-*` roles or other app-access-only entitlements
- confirm `platform-admin` has write policy membership
- confirm `platform-user` and `platform-viewer` have read policy membership
- confirm Superset and DataHub are visible to all three roles
- confirm JupyterHub and CloudBeaver are visible to `platform-admin` and `platform-user`, but not `platform-viewer`
- confirm admin-only tools are visible only to `platform-admin`
- confirm no sync job requires Ranger Postgres credentials

## Acceptance criteria

This iteration is complete when:

- the chart owns and renders the three built-in platform roles
- the infra overlays supply the three deployment-owned group names and their role mappings
- LDAP is supported as the source of truth for users and groups when LDAP is configured
- Keycloak local users and groups are supported as the source of truth when LDAP is not configured
- Keycloak is the only routine membership source for platform roles
- Ranger users, groups, and roles are synchronized through the correct LDAP or Keycloak-local path
- Ranger is not supported as a source of truth for roles or role membership
- `platform-app-*` roles or groups are not part of the new access model and are not synchronized to Ranger
- no new or retained sync path writes directly to the Ranger database
- the icddr,b dev and prod overlays use the new three-role/three-group model
- docs and SOPs tell operators to manage users/groups in LDAP or Keycloak-local mode as appropriate, and platform role membership in Keycloak
- render-contract and infra manifest checks pass

## Suggested smaller steps

1. Chart access-model contract and validation
2. Keycloak roles, groups, and app-access rendering
3. Keycloak-to-Ranger API sync without database writes
4. icddr,b overlay and policy migration
5. Documentation, render tests, and cluster validation
