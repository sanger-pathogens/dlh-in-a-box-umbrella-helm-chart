# dlh-in-a-box Chart Guide

This guide is for people who consume or maintain the `dlh-in-a-box` Helm
chart. If you need environment-specific deployment steps, use the downstream
infra repository instead.

## What This Chart Does

`dlh-in-a-box` packages a modular lakehouse platform as one Helm release. It
prefers upstream charts and keeps local logic limited to the places where the
components need to be composed together.

```mermaid
flowchart LR
  Values[Helm values] --> Umbrella[dlh-in-a-box chart]
  Umbrella --> Portal[Platform Home]
  Umbrella --> Trino[Trino]
  Umbrella --> Prefect[Prefect plus oauth2-proxy]
  Umbrella --> CloudBeaver[CloudBeaver plus oauth2-proxy]
  Umbrella --> Keycloak[Keycloak optional]
  Umbrella --> Ranger[Ranger optional]
  Umbrella --> DataHub[DataHub optional]
  Umbrella --> Superset[Superset optional]
  Umbrella --> Hive[Generated Hive metastores]
```

## Supported Identity Modes

The chart now supports two first-class identity modes:

- `externalLdap`: bundled Keycloak for browser SSO, institutional LDAP or AD
  for user and group discovery, optional Trino LDAP password auth, Ranger
  usersync, and the portal `Access Control` workspace for routine membership
  edits.
- `keycloakLocal`: bundled Keycloak for browser SSO and self-registration,
  Ranger-driven platform-role membership projected into Keycloak
  `platform-role-*` and `platform-app-*` groups, Ranger direct-user data-role
  grants, and OIDC/token-capable Trino clients for ordinary users instead of
  routine direct password auth.

## Default Architecture

The default documented shared-environment model remains `externalLdap`:

- `Keycloak` issues OIDC tokens.
- `Organizational LDAP or Active Directory` supplies users and groups in every environment.
- `Active Directory over LDAPS` supplies users and groups in production.
- `Trino` authenticates with OIDC and optional file-based, LDAP, or mixed
  LDAP-plus-file password auth. File-based Trino access rules remain the default unless
  `global.authorization.ranger.trino.enabled=true` is set for a Ranger-capable
  Trino image. The LDAP group-provider path is opt-in through
  `global.identity.external.clients.trino.groupProviderEnabled` because not
  every Trino image bundles that module. If Trino needs a different LDAP bind
  pattern from the shared directory defaults, use
  `global.identity.external.clients.trino.ldapUserBindPattern`.
- `Superset`, `DataHub`, and the `Prefect` proxy trust the same OIDC issuer.
- optional `JupyterHub` can trust that same OIDC issuer and forward the
  resulting Keycloak access token into spawned notebook servers.
- `Ranger`, `CloudBeaver`, and `Prefect` reuse that same browser session
  through chart-managed auth proxies.
- deployment-owned admin tools such as `MinIO Console`, standalone `Vault`,
  and `Headlamp` can reuse the same Keycloak realm through reusable OIDC
  client blocks owned by the umbrella chart.
- the portal can optionally launch Vault through a short-lived wrapped Vault
  login token derived from the caller's current Keycloak bearer token, so the
  admin card can land directly in Vault's native UI session without a second
  in-app click.
- `platformHome` is the default browser entrypoint, renders grouped launch
  cards, exposes health/status information, and only hides links based on
  Keycloak group claims.
- `platformHome` also exposes an admin-only `/access-control` destination for
  LDAP-backed role assignment and governed direct-user exceptions when the
  chart runs in `externalLdap` mode, with Ranger as the live membership
  backend when enabled.
- `oauth2-proxy` protects Prefect, CloudBeaver, and the Ranger browser path
  because all three are front-door integrations around the same Keycloak
  session.
- when enabled, JupyterHub becomes another browser destination behind the same
  realm rather than a separate identity stack.

The chart still supports an externally managed OIDC provider, but that is the
escape hatch, not the main reference architecture.

## Start With These Docs

- Fast evaluation path:
  [../../docs/quickstart.md](../../docs/quickstart.md)
- Identity, LDAP/AD, Ranger, and Prefect access model:
  [../../docs/auth-architecture.md](../../docs/auth-architecture.md)
- Governance metadata, Ranger policy expectations, and new data source rules:
  [../../docs/data-governance.md](../../docs/data-governance.md)
- Terminology:
  [../../docs/glossary.md](../../docs/glossary.md)
- Example values files:
  [../../examples/README.md](../../examples/README.md)

## Values You Will Touch Most Often

| Values path | Why it exists |
| --- | --- |
| `global.identity` | Shared identity contract. Define the identity mode, issuer, clients, directory settings, Keycloak registration behavior, and any local bootstrap fallback here. |
| `global.authorization` | Ranger contract and bootstrap policy surface. |
| `global.authorization.platformRoles` | Git-managed data-access roles that map directory groups or approved direct users into Ranger roles. |
| `global.dataCatalogs` | Catalog definitions, access groups, and governance metadata. |
| `global.dataCatalogs.*.governance` | Required non-local dataset classification and approval metadata. |
| `platformHome` | Lightweight launchpad UI served by NGINX plus a small same-origin API for health aggregation and the dedicated `/access-control` admin workspace. |
| `cloudbeaver` and `cloudbeaver-auth-proxy` | CloudBeaver Community Edition plus its Keycloak-backed reverse-proxy front door. |
| `prefect.authProxy` and `prefect-auth-proxy` | Prefect front-door protection with OIDC. |
| `keycloak` | Bundled Keycloak deployment settings, including trusted CA input for LDAPS federation. |

## Governance And Policy

Every non-local catalog now needs a `governance` block. That block exists to
stop the chart from exposing a dataset before it has been classified and tied
to an approval path.

At a minimum, the chart expects:

- data classification
- whether the dataset contains direct or quasi identifiers
- IRB state
- sharing state
- PI owner and data steward
- source system
- approval reference
- retention notes

The chart can enforce approved access patterns. It cannot decide whether a
dataset should be approved in the first place. Those approvals still belong to
your institutional governance process.

## Platform Roles And Exceptions

The chart now has a first-class platform-role contract under
`global.authorization.platformRoles`.

Use it for the long-lived baseline:

- map institutional directory groups to named Ranger roles
- add direct service users when a policy genuinely needs them
- compose additive bundles with nested roles

Then point `global.authorization.ranger.bootstrapPolicies` at those roles.

If one person needs extra access temporarily, do not silently broaden the base
role. Create a short-lived exception role with approval metadata and expiry.
The bundled exception-audit CronJob can then flag or delete expired exceptions.

## Prefect Authentication

Use `oauth2-proxy` in front of Prefect and let it redirect to Keycloak. Do not
rely on Prefect OSS native login as the real security boundary.

If you want a branded login experience, customize the Keycloak theme and set
`global.identity.provider.keycloak.loginTheme`. Do not build a custom Prefect login
page.

The Keycloak login-page header text can be set separately with
`global.identity.provider.keycloak.displayName`.

For programmatic access from outside the cluster, enable
`global.identity.external.clients.prefectAutomation.enabled=true`. This keeps
browser login behavior unchanged while allowing bearer JWT access on
`/api/*` through `oauth2-proxy` when issuer and audience match.

Use a dedicated audience such as `prefect-api` and avoid reusing it across
other applications. In bundled Keycloak mode, provide the machine-client
secret through
`global.identity.external.clients.prefectAutomation.configCliSecretKey`.

For developer workstations that should exchange the same Keycloak username and
password for a bearer token without a popup browser flow, enable
`global.identity.external.clients.prefectDirectGrant.enabled=true`. That
client is public, uses direct grants, and should share the same Prefect API
audience as the machine client when both are enabled.

## Portal And CloudBeaver

`platformHome` is the default browser entrypoint. It uses a public Keycloak
client, reads `groups` claims in the browser, and shows only the grouped app
cards the user should see after sign-in. Anonymous users only see the product
branding and a sign-in action. It does not replace downstream authorization.

Platform administrators also get a first-class portal administration
experience:

- grouped admin-tool launch cards
- a dedicated `Access Control` route backed by the same-origin admin API in
  `externalLdap` mode only
- LDAP-backed discovery of users and groups, with Ranger as the live write
  target for role membership in `externalLdap` mode
- governed direct-user exceptions with stored metadata and expiry in
  `externalLdap` mode
- optional links to downstream admin tools such as Ranger Admin, which reuses
  the same browser session as the portal

Portal role management and Ranger policy/bootstrap remain reusable chart
features even when Trino itself stays on file-based access-control. Enable
`global.authorization.ranger.trino.enabled=true` only when the Trino image also
ships the Ranger plugin.

Git remains the source of truth for role definitions, app entitlements, and
nested role topology. When
`global.authorization.platformRoleMembershipSource=ranger`, the portal writes
live user or group membership to Ranger so those changes survive later chart
reconciliation.

In `keycloakLocal` mode the portal intentionally hides the `Access Control`
workspace instead of exposing a half-working LDAP-oriented UI. Direct-user
membership in Ranger platform roles is projected back into the matching
`platform-role-*` and browser `platform-app-*` Keycloak groups so browser
entitlements stay aligned with the live Ranger role catalog. The supported
admin split in that mode is:

- Keycloak Admin for account lifecycle and any standalone browser app-group
  overrides such as `platform-app-*`
- Ranger Admin for direct-user platform-role and Trino data-role membership plus
  policy audit
- Trino OIDC/token-capable clients for routine DBeaver, Python, or R access
- optional JupyterHub notebook servers that receive the same Keycloak-backed
  Trino bearer token at spawn time

Deployments may also keep a named bootstrap admin in Trino file-password auth
for smoke validation or recovery. That is an operational exception, not the
normal user model.

## Keycloak Local Users Mode

Use `global.identity.directory.mode=keycloakLocal` when an institution wants
bundled Keycloak to own human accounts directly instead of federating to LDAP.

That mode requires:

- `global.identity.provider.mode=bundledKeycloak`
- `global.identity.provider.keycloak.registration.enabled=true`
- `global.identity.provider.keycloak.registration.requireEmailVerification` set
  to match whether SMTP-backed verification is actually available
- `global.identity.directory.ldap.enabled=false`
- `global.identity.external.clients.trino.passwordAuthEnabled=false` for human
  users, or `true` only with `passwordAuthMode=file` when you need non-human
  service accounts such as `superset-service` or `cloudbeaver-service`
- `global.authorization.ranger.usersync.enabled=false`

The intended user lifecycle is:

1. a user self-registers in Keycloak
2. an administrator grants platform-role membership in Ranger
3. the local-user sync automation projects those Ranger roles into the
   matching Keycloak `platform-role-*` and `platform-app-*` groups
4. an administrator grants Trino data access in Ranger
5. the user accesses browser apps via Keycloak SSO and Trino via OIDC/token
   clients

The supported non-browser Trino patterns in this chart are now:

- browser-capable clients such as DBeaver using the Trino OIDC/external-auth flow
- a Keycloak direct-grant client such as `trinoDirectGrant` when an
  institution explicitly wants Python, R, or CLI tooling to exchange the same
  Keycloak username and password for a bearer token without opening a browser
- notebook environments such as JupyterHub that reuse the already-issued
  Keycloak token instead of prompting for another password inside the notebook

The initial JupyterHub integration is intentionally conservative:

- per-user notebook servers and storage
- a preloaded Trino demo notebook and kernel
- Keycloak-backed browser login plus token reuse inside the notebook

Collaborative notebook sharing or team-published workspaces can be layered on
later, but they are not part of the first chart-level contract.

When `cloudbeaver.bootstrap.sharedConnectionSeed.enabled=true`, the chart can
seed the shared datasource definition into the workspace together with the
pre-configured connection permissions for the CloudBeaver teams that should see
it. In the reverse-proxy browser model, the reliable pattern is to embed the
shared Trino service credential directly into the seeded datasource definition
in the downstream repo, alongside the manual-mode `host`, `port`,
catalog/database, schema, and TLS truststore properties. The chart bootstrap
then only grants that seeded connection to the intended teams; it no longer
needs to persist shared credentials through a transient browser session.
Keeping `cloudbeaver.app.adminCredentialsSaveEnabled=true` is still useful for
local admin maintenance, and you can still override
`cloudbeaver.app.secretManagerEnabled` explicitly when needed.
Downstream repos should seed the Trino datasource in true manual-mode form
(`host`, `port`, catalog/database, and driver properties such as TLS
truststore settings), not only as a raw JDBC URL, so the saved connection stays
editable and valid in the CloudBeaver admin UI. The chart bootstrap then uses
the reverse-proxy header identity to grant the seeded connection to those
teams without requiring a separate local CloudBeaver login flow. Downstream
Trino access-control rules should also explicitly deny the `system` catalog to
ordinary end users so browser clients only see the intended business catalogs.

In that service-account model the common Trino identities are:

- `cloudbeaver-service`: shared CloudBeaver datasource credential
- `superset-service`: shared Superset datasource credential
- `trino`: Ranger service identity used in the Ranger service definition and
  plugin download settings, not a normal human login

Only services that actually open Trino sessions should get a dedicated Trino
identity. The `trino` identity is not meant for human access and does not open
interactive SQL sessions; it exists so Ranger can identify the Trino service
itself when the plugin downloads policies and reports back. Human break-glass
access should use a deliberately named account such as `icddrb-admin`, not a
generic `admin` credential. Some deployments may choose to mirror that
bootstrap human admin into Trino file-password auth for smoke validation or
recovery, but that should remain an explicit, named exception rather than the
default human access pattern. In the current shared chart model that means
CloudBeaver and Superset. Other browser applications such as the portal,
Keycloak, Prefect, or DataHub should not get extra Trino passwords unless they
really submit Trino queries, because unused service credentials make audit
trails noisier rather than clearer.

## Portal Theming And Branding

The umbrella chart owns the reusable portal behavior. Consumer repositories own
deployment-specific branding.

That split is intentional:

- keep structure, auth flow, app grouping, health rendering, and admin UX in
  this chart
- keep organization-specific titles, logos, colors, fonts, favicons, and any
  one-off visual polish in downstream values overlays

The main values surface is:

| Values path | Purpose |
| --- | --- |
| `platformHome.branding.title` | Portal title shown in the page and browser chrome. |
| `platformHome.branding.subtitle` | Optional subtitle below the title. |
| `platformHome.branding.logoUrl` | Optional logo image. |
| `platformHome.branding.logoAlt` | Accessible text for the logo. |
| `platformHome.branding.faviconUrl` | Optional favicon for browser tabs. |
| `platformHome.theme.metaThemeColor` | Browser theme color for mobile/browser UI. |
| `platformHome.theme.colors.*` | CSS custom properties for background, surface, brand, accent, and line tokens. |
| `platformHome.theme.fonts.bodyFamily` | Body font-family stack. |
| `platformHome.theme.fonts.headingFamily` | Heading font-family stack. |
| `platformHome.theme.fonts.preloads[]` | Optional preload links for remote or hosted font assets. |
| `platformHome.theme.fonts.fontFaces[]` | Optional `@font-face` declarations emitted by the template. |
| `platformHome.theme.customCss` | Small deployment-specific CSS escape hatch. |
| `platformHome.ingress.additionalHosts[]` | Optional extra ingress hostnames that should serve the same portal frontend and TLS secret as the primary `platformHome.ingress.host`. |

Minimal neutral example:

```yaml
platformHome:
  enabled: true
  branding:
    title: Data Platform
    subtitle: Shared analytics environment
  theme:
    colors:
      brand: "#1f5f7a"
      accent: "#e58a18"
```

Branded example:

```yaml
platformHome:
  enabled: true
  branding:
    title: Example Institute Data Platform
    subtitle: Secure access to approved tools and services
    logoUrl: https://example.org/assets/platform-logo.svg
    logoAlt: Example Institute logo
    faviconUrl: https://example.org/assets/favicon.ico
  theme:
    metaThemeColor: "#7a1331"
    fonts:
      bodyFamily: '"Source Sans Pro", sans-serif'
      headingFamily: '"Example Serif", Georgia, serif'
      preloads:
        - href: https://example.org/assets/fonts/example-serif.woff2
          as: font
          type: font/woff2
          crossorigin: anonymous
      fontFaces:
        - family: Example Serif
          src: 'url("https://example.org/assets/fonts/example-serif.woff2") format("woff2")'
          weight: "700"
          style: normal
    colors:
      brand: "#7a1331"
      brandDeep: "#571024"
      accent: "#cf8d2e"
```

## Portal Icons And Health

Each portal item can now carry icon and health metadata through values so the
reusable chart can render a polished launchpad without hard-coding any
institution-specific assets.

Use `platformHome.itemMeta.<id>` for chart-owned items such as `superset`,
`datahub`, `jupyterhub`, `prefect`, `cloudbeaver`, `trino`, `ranger-admin`, or
`keycloak-admin`, and set equivalent fields directly on
`platformHome.adminTools[]` for custom admin cards.

If the consumer repo also needs Keycloak-managed OIDC clients for external
portal-linked tools, the umbrella chart now exposes reusable client blocks for:

- `global.identity.external.clients.minio`
- `global.identity.external.clients.vault`
- `global.identity.external.clients.headlamp`
- `global.identity.external.clients.jupyterhub`
- `global.identity.external.clients.trinoDirectGrant`

Supported fields are:

| Values path | Purpose |
| --- | --- |
| `iconUrl` | Optional image URL or hosted asset path for the card icon. |
| `iconAlt` | Accessible text for the icon image. |
| `iconBackground` | Optional background color behind the icon. |
| `iconText` | Fallback initials when no image is configured. |
| `health.targetUrl` | Endpoint checked by the same-origin portal backend. |
| `health.expectedStatusCodes[]` | Allowed HTTP codes for a healthy or degraded response. |
| `health.bodyIncludes` | Optional response-body marker for lightweight content checks. |
| `health.timeoutSeconds` | Per-probe timeout. |
| `health.public` | Whether the target is intended to be browser-public. |

When `platformHome.health.enabled=true`, the portal exposes `GET /api/health`
and renders periodic status badges such as `Healthy`, `Degraded`, `Down`, or
`Unknown` on the launch cards.

CloudBeaver is intentionally different from the browser-only apps:

- browser access goes through `oauth2-proxy` and Keycloak
- downstream repos can optionally seed a default CloudBeaver workspace and
  datasource set through `cloudbeaver.bootstrap.workspaceSeedExistingSecret`
- downstream repos can mount a database CA into a generated JVM trust store
  through `cloudbeaver.trustedCa.*` when the saved datasource should verify TLS
- the reusable chart only provides the workspace-seed contract; the actual
  datasource definitions, including manual-mode host/port details and any
  development-only stored credentials, live in consumer repos
- Ranger still decides what data the resulting Trino session may read or mask

## LDAPS And Trust Material

When the chart talks to LDAP or AD over LDAPS, use one of these trust modes:

1. provide a custom CA Secret through
   `global.identity.directory.ldap.trustedCaExistingSecret`
2. mirror that same Secret to `keycloak.trustedCertsExistingSecret`
3. or, when the directory already chains to a public CA trusted by the base
   images, set `global.identity.directory.ldap.useSystemTrustStore=true`

The chart validates that Keycloak, Trino, and Ranger all use the same trust
mode.

## Keycloak Client Secret Contract

When bundled Keycloak is enabled, the chart expects one Kubernetes Secret to
provide the config-cli environment variables consumed during realm bootstrap.

- Values path:
  `global.identity.provider.keycloak.configCliEnvExistingSecret`
- Default Secret name:
  `dlh-keycloak-config-cli-env`
- Required keys:
  `LDAP_BIND_PASSWORD`
  `KC_TRINO_CLIENT_SECRET`
  `KC_SUPERSET_CLIENT_SECRET`
  `KC_DATAHUB_CLIENT_SECRET`
  `KC_JUPYTERHUB_CLIENT_SECRET`
  `KC_CLOUDBEAVER_CLIENT_SECRET`
  `KC_PREFECT_CLIENT_SECRET`
  when `global.identity.external.clients.prefectAutomation.enabled=true`, also
  include `KC_PREFECT_AUTOMATION_CLIENT_SECRET` (or the custom
  `configCliSecretKey` value)
- `prefectDirectGrant` does not need a client secret because it is a public
  direct-grant client
- Optional local/dev-only keys:
  any `passwordEnvVar` referenced by
  `global.identity.provider.keycloak.bootstrapUsers`, for example
  `KC_BOOTSTRAP_ADMIN_PASSWORD`

Only include the client secret keys for the clients you actually enable, but
the secret name itself is now part of the supported contract.

## Example Overlays

- `examples/values-dev.yaml`
  Bundled Keycloak + external LDAP/AD + Ranger development pattern with the
  portal, optional JupyterHub, and CloudBeaver enabled.
- `examples/values-prod.yaml`
  Bundled Keycloak + external LDAPS + Ranger production-shaped pattern with the
  portal, optional JupyterHub, and CloudBeaver enabled.
- `examples/values-shared-auth.yaml`
  External OIDC escape hatch with CloudBeaver still behind `oauth2-proxy`.

## Reference-Only Material

The vendored upstream Trino chart and other dependency archives under
`charts/dlh-in-a-box/charts/` are reference-only. They are useful when you
need to inspect upstream behavior, but the primary chart API is documented in
this guide and the docs linked above.

## Validation

Validate from the repository root:

```bash
./hack/helm-dependency-update.sh
./hack/lint.sh
./hack/template.sh
```

For a rendered local install proof point, use:

```bash
make smoke-install
```
