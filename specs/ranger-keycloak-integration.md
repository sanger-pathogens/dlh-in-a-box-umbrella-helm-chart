# Spec for Ranger-Keycloak integration

## Mission

Keycloak is the central identity provider for the platform.
It exposes users, groups, platform roles, and application access entitlements to platform applications.

When LDAP is configured, LDAP is the source of truth for users and groups, and Keycloak federates those users and groups.
When LDAP is not configured, Keycloak local users and groups are the source of truth.

Keycloak is always the source of truth for platform roles and platform role membership.
Ranger receives a projection of users, groups, platform roles, and platform role membership so policies can target roles.

Definitions:

- User: a person or a service account.
- Group: a collection of users.
- Role: a collection of permissions.

The built-in human platform roles are:

1. `platform-admin`
2. `platform-user`
3. `platform-viewer`

The icddr,b deployment groups are:

1. `admins`
2. `data-analyst`
3. `principal-investigator`

Initial group-to-role mapping:

| Keycloak group | Keycloak realm role | Ranger role | Browser app access |
| --- | --- | --- | --- |
| `admins` | `platform-admin` | `platform-admin` | all enabled platform components |
| `data-analyst` | `platform-user` | `platform-user` | Superset, DataHub, JupyterHub, CloudBeaver |
| `principal-investigator` | `platform-viewer` | `platform-viewer` | Superset, DataHub |

Application access can also be expressed through client roles such as `prefect:access`, `datahub:access`, or `cloudbeaver:access`.
Client roles are for browser/application access and must not be synchronized to Ranger unless they are explicitly modeled as platform data roles.

For Ranger in this iteration:

- `platform-admin` gets write-level policy membership.
- `platform-user` gets read-level policy membership.
- `platform-viewer` gets read-level policy membership.
- Full Ranger-Trino authorization hardening is left for the next iteration.

## Current Contract

The chart source of truth is `global.identity.accessModel`.

```yaml
global:
  identity:
    accessModel:
      builtinRoles:
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

Role names are synchronized from Keycloak to Ranger exactly as-is.
There is no `ranger.roleName` override.

The built-in role key is `builtinRoles`, with `builtin` all lowercase.
The old `builtInRoles` spelling is not part of the contract.

The old `global.authorization.platformRoles` model is not part of the target contract.
It must not be used as an input by chart examples, infra overlays, sync code, Platform Home, or browser access configuration.
Validation may mention it only to reject it.

The old `global.authorization.platformRoleMembershipSource` switch is not part of the target contract.
Keycloak is the only supported routine source for platform role definitions and platform role membership.
There is no `git` fallback and no Ranger-as-source mode.

`global.authorization` remains only for Ranger runtime, policy, exception, and service configuration that is not a platform-role source of truth.
A future cleanup may move remaining Ranger-specific keys under a clearer namespace, but that is outside this iteration.

## Identity Flows

### LDAP Mode

LDAP mode is active when `global.identity.directory.ldap.enabled=true`.

In LDAP mode:

- LDAP owns users and groups.
- Keycloak federates users and groups from LDAP.
- Ranger Usersync reads users and groups from the same LDAP server.
- Keycloak owns platform roles and role membership.
- Keycloak group-to-role mappings can be rendered for LDAP-backed group names as they appear in Keycloak.
- The Keycloak-to-Ranger role sync reads Keycloak role membership and updates Ranger roles through Ranger APIs.
- The role sync must not create duplicate Ranger users or groups already supplied by Ranger Usersync.

### Keycloak-Local Mode

Keycloak-local mode is active when LDAP is not configured.

In Keycloak-local mode:

- Keycloak owns users and groups.
- Keycloak owns platform roles and role membership.
- The chart-managed Keycloak-to-Ranger sync creates or updates Ranger users and groups through Ranger APIs.
- The chart-managed Keycloak-to-Ranger sync creates or updates Ranger roles through Ranger APIs.

## Browser Access

Browser applications should authorize through roles, not through legacy access groups.

OAuth2 proxy clients use the `keycloak-oidc` provider and `allowed_roles` for client roles such as:

- `prefect:access`
- `cloudbeaver:access`
- `ranger:access`

The generic `oidc` provider is not sufficient for this path because the oauth2-proxy Keycloak role checks rely on the Keycloak-specific provider behavior.

The old `global.identity.external.clients.*.allowedGroups` key is not part of the contract.
It should fail validation if set.

Platform Home launchers use `requiredRoles`.
The old `requiredGroups` key is not supported and should fail validation if set.

Platform Home reads the configured OIDC roles claim, defaulting to `platform_roles`.
Its admin API authorizes administrators through roles, defaulting to `platform-admin`.

## Bootstrap Users and Service Accounts

Human bootstrap users should join the access model through groups.
For the icddr,b dev bootstrap path, `icddrb-admin` should be assigned to the `admins` group, and the `admins` group should receive `platform-admin` through `groupRoleMappings`.

Service accounts should not depend on the removed `global.authorization.platformRoles` model.
They should receive only the roles they need through the component-specific provisioning path that creates or synchronizes that service account.
For example, a Prefect automation service account that needs Prefect browser/API access should receive the `prefect:access` client role.

Service-account grants that need platform data authorization must be modeled explicitly as Keycloak roles and then projected to Ranger through the same Keycloak-to-Ranger sync path.
Service-account grants that are app-only client roles must not be projected to Ranger.

## Ranger Sync Requirements

Apache Ranger Usersync is used for users and groups when LDAP is configured.
It cannot synchronize Keycloak roles, so platform roles and platform role membership always need the Keycloak-to-Ranger role sync path.

Any custom sync script must use Ranger APIs.
No implementation may read or write Ranger database tables directly.

The chart-managed sync must:

- authenticate to Keycloak Admin API
- read configured platform roles from Keycloak
- read platform role membership from Keycloak
- create or update Ranger roles with the exact same names as Keycloak roles
- assign Ranger role users and groups from Keycloak role membership
- ignore Keycloak client roles and application-only access entitlements when building Ranger data-authorization state
- create or update Ranger users and groups only in Keycloak-local mode
- avoid pruning arbitrary operator-created Ranger state
- avoid rendering Ranger Postgres credentials
- avoid importing `psycopg` or installing `psycopg[binary]`

The infra repository must not contain a routine sync path that reads or writes Ranger database tables.
The retained development sync wrapper should only trigger the chart-managed Keycloak-to-Ranger CronJob.

## Implemented So Far

The chart currently has:

- `global.identity.accessModel.builtinRoles`
- `global.identity.accessModel.additionalRoles`
- `global.identity.accessModel.groupRoleMappings`
- exact Keycloak role-name synchronization to Ranger
- no `ranger.roleName` override
- validation that rejects `global.authorization.platformRoles`
- validation that rejects `global.authorization.platformRoleMembershipSource`
- validation that rejects `global.identity.external.clients.*.allowedGroups`
- validation that rejects Platform Home launcher `requiredGroups`
- Keycloak realm role rendering from the access model
- Keycloak group-to-role mapping from the access model
- Keycloak client role rendering for app access
- `platform_roles` as the default roles claim
- oauth2-proxy clients using `provider = "keycloak-oidc"` and `allowed_roles`
- Platform Home using `requiredRoles`
- Platform Home admin authorization through roles
- Superset mapping OAuth login claims from `platform_roles` to Superset roles
- JupyterHub allowing/admining users from `platform_roles`
- DataHub OIDC login configured without group-claim provisioning
- Keycloak-to-Ranger role sync through Ranger APIs
- Keycloak-local user and group sync through Ranger APIs
- no chart-managed Keycloak-to-Ranger Postgres dependency

The infra overlays currently have:

- access-model mappings for `admins`, `data-analyst`, and `principal-investigator`
- policy references migrated to `platform-admin`, `platform-user`, and `platform-viewer`
- the bootstrap admin script assigning `icddrb-admin` to `admins`
- Prefect automation service-account sync granting `prefect:access`
- render checks updated for the role-based contract
- Superset role mappings changed from deployment groups to platform roles
- JupyterHub access changed from deployment groups to platform roles
- DataHub group-provisioning values removed
- direct Ranger database sync removed from the development Keycloak-to-Ranger path
- `sync_keycloak_local_users_to_ranger.sh` retained only as a wrapper that triggers the chart-managed sync CronJob

## Remaining Implementation Steps

### 1. Add strict direct-URL enforcement for DataHub if required

Superset and JupyterHub can consume `platform_roles` directly for browser access.
DataHub's current chart OIDC settings authenticate users but do not provide a built-in role gate equivalent to oauth2-proxy `allowed_roles`.
The old DataHub group-provisioning values are unused and removed.

If direct DataHub URL access must be restricted to `platform-admin`, `platform-user`, and `platform-viewer`, add an oauth2-proxy in front of DataHub or another DataHub-supported role gate.
Do not reintroduce group-claim access for this.

Audit service accounts such as CloudBeaver, Superset, and Prefect automation accounts, and make sure each one receives required client roles or platform roles from its own provisioning path rather than from `global.authorization.platformRoles`.

### 2. Update operational docs and examples

Update infra documentation and examples so operators see the new process:

- in LDAP mode, create users and manage source group membership in LDAP
- in Keycloak-local mode, create users and manage source group membership in Keycloak
- manage platform role membership in Keycloak, usually through group-to-role mappings
- inspect projected Ranger roles in Ranger
- manage Ranger policies in Ranger
- do not manage routine platform role membership in Ranger
- do not grant browser access through `platform-app-*` groups
- do not configure `global.authorization.platformRoles`
- do not configure `global.authorization.platformRoleMembershipSource`

At minimum update:

- `docs/concepts/auth-and-access.md`
- `docs/architecture/browser-access-and-sso.md`
- `docs/access/sops/assign-directory-users-and-groups-to-platform-roles.md`
- `docs/access/sops/grant-browser-access-in-keycloak.md`
- `docs/access/sops/grant-data-access-in-ranger.md`
- `docs/access/sops/create-or-change-platform-role.md`
- `platform/dlh-in-a-box/values-dev.local.yaml.example`
- `platform/dlh-in-a-box/scripts/README.md`

### 3. Validate render and cluster behavior

Chart repository validation:

```bash
python3 -m json.tool charts/dlh-in-a-box/values.schema.json >/dev/null
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
- confirm Keycloak tokens contain expected realm roles and client roles
- confirm Ranger contains users and groups from LDAP or Keycloak-local mode as appropriate
- confirm Ranger contains `platform-admin`, `platform-user`, and `platform-viewer`
- confirm Ranger role membership is projected from Keycloak
- confirm Ranger does not contain `platform-app-*` roles from browser access
- confirm `platform-admin` has write policy membership
- confirm `platform-user` and `platform-viewer` have read policy membership
- confirm Superset and DataHub are visible to all three roles
- confirm JupyterHub and CloudBeaver are visible to `platform-admin` and `platform-user`, but not `platform-viewer`
- confirm admin-only tools are visible only to `platform-admin`
- confirm no sync job requires Ranger Postgres credentials

## Acceptance Criteria

This integration is complete when:

- the chart owns and renders the three built-in platform roles
- the infra overlays supply deployment-owned group names and role mappings
- LDAP remains the user/group source of truth when LDAP is configured
- Keycloak local users and groups are supported when LDAP is not configured
- Keycloak is the only routine source for platform roles and platform role membership
- Ranger receives platform roles and role membership from Keycloak
- Ranger role names exactly match Keycloak role names
- Ranger is not supported as a source of truth for platform roles or role membership
- `global.authorization.platformRoles` is rejected and unused
- `global.authorization.platformRoleMembershipSource` is rejected and unused
- `platform-app-*` groups or roles are not part of the new access model
- `allowedGroups` and `requiredGroups` are rejected and unused
- no retained sync path reads or writes the Ranger database directly
- docs and SOPs explain where to manage users, groups, roles, app access, and Ranger policies
- chart render-contract checks pass
- infra manifest checks pass
