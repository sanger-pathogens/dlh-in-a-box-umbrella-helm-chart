# CloudBeaver Subchart

This folder contains a self-contained CloudBeaver Community Edition chart. It
knows how to run one CloudBeaver deployment (Service, Deployment, ConfigMap,
optional workspace PersistentVolumeClaim) protected by an external oauth2-proxy
auth boundary — it has no notion of "data lakehouse" or anything else specific
to the umbrella chart it happens to live inside.

## What This Subchart Does

- deploys CloudBeaver with a ConfigMap-driven `cloudbeaver.conf` (`server`
  block, read once at cold start) / `cloudbeaver.runtime.conf` (`app` block,
  built from `app.config` -- an open passthrough for any CloudBeaver `app:`
  setting, merged under a handful of chart-derived auth-wiring keys --
  force-reapplied to the workspace on every pod start so Helm values always
  win over persisted/admin-UI-edited state)
- accepts arbitrary extra container env vars via `extraEnv`, e.g. to reach
  the `CLOUDBEAVER_*` placeholders already baked into `cloudbeaver.conf`'s
  `server` block, or to set `CB_SERVER_NAME`
- registers CloudBeaver's own auth providers additively: `auth.proxy`
  (`reverseProxy`, delegated to an external Keycloak-backed oauth2-proxy) and
  `auth.local` (native `cbadmin` login) can both be enabled at once — see
  [Auth model](#auth-model). Both are live/continuously reconciled, unlike
  everything under `seed.*` below.
- `seed.*` is one-time, first-boot-only provisioning (or after
  `seed.force=true` resets the workspace back to fresh):
  `seed.admin` unconditionally provisions the native admin identity (it's
  the break-glass path even when `auth.local.enabled=false` day-to-day),
  and `seed.teams` seeds CloudBeaver's initial teams/permissions from a
  plain structured list (no Secret needed — nothing in it is sensitive).
- `connections` governs CloudBeaver's global (shared) connections list,
  separately from `seed.*` — this file is CloudBeaver's own live
  write-back store, so any connection a user creates or edits through the
  UI is persisted into the same `data-sources.json` the chart would seed.
  `connections.manage=false` (default) means Helm never touches the file
  at all; `manage=true` fully overwrites it from `existingSecret` on every
  pod start, discarding anything created/changed through the UI since the
  last deploy — the same force-reapply tradeoff as `app.config` above.
  `connections.permissions` (team → connection access grants, CloudBeaver's
  own `data-sources-permissions.json`) is only meaningful when
  `manage=true`, since connection ids are otherwise unpredictable; when
  active it's re-read and fully reconciled by CloudBeaver's own boot
  sequence on every pod start, not one-time.
- optionally trusts extra CAs (`trustedCerts`), for talking to a Trino/DB
  TLS endpoint signed by an internal CA -- every key in the referenced
  secret is imported by CloudBeaver at startup and trusted for all
  connections, so no per-connection SSL setup is needed

## Files In This Folder

| Path | What it is for |
| --- | --- |
| `Chart.yaml` | chart metadata; no dependencies of its own |
| `values.yaml` | every CloudBeaver-owned setting (see below) |
| `templates/_helpers.tpl` | naming/label helpers, and the Service name helper the umbrella's own oauth2-proxy config also calls |
| `templates/validation.yaml` | this chart's own self-contained `fail()` guards |
| `templates/configmap.yaml` | `cloudbeaver.conf` / `cloudbeaver.runtime.conf` |
| `templates/pvc.yaml` | optional workspace PersistentVolumeClaim |
| `templates/service.yaml` | the Service |
| `templates/deployment.yaml` | the Deployment, including init containers |

## Auth model

`auth.proxy.enabled` is the SSO login path (Keycloak via an external
oauth2-proxy in front of this Service) — the umbrella chart's own
`identity-validation.yaml` makes this unconditionally mandatory whenever
`cloudbeaver.enabled=true`, so CloudBeaver always sits behind the platform's
central authentication boundary; that policy lives at the umbrella level
because it needs cross-cutting `global.identity` context this chart doesn't
have on its own.

`auth.local.enabled` is CloudBeaver's native username/password login,
additive on top of `auth.proxy` rather than a substitute for it:
`enabledAuthProviders` is built as an additive list (see
`templates/configmap.yaml`), not an exclusive choice. On the normal path
(behind oauth2-proxy), the forwarded-username header is present on every
request, so CloudBeaver auto-authenticates via `reverseProxy` and the local
login screen never surfaces. `auth.local` only becomes reachable if
something bypasses oauth2-proxy and hits this chart's Service directly with
no forwarded-username header present — the deliberate break-glass path.

This chart's own `templates/validation.yaml` additionally requires that at
least one of `auth.local.enabled` / `auth.proxy.enabled` be true, that
`seed.admin.existingSecret` be set, and that `serverName` is never empty
(CloudBeaver's env-var-driven auto-configuration -- which is what applies
`seed.admin`'s credentials -- only runs when `CB_SERVER_NAME` is present
alongside `CB_ADMIN_NAME`/`CB_ADMIN_PASSWORD`) — all self-contained checks
that don't need any context beyond this chart's own values, so they hold
even if this chart is ever rendered standalone, independent of the
umbrella's own (stricter) policy above.

## Common Tasks

If you need to:

- change `cloudbeaver.conf`/`cloudbeaver.runtime.conf` generation: edit
  `templates/configmap.yaml`
- change container/init-container/volume behavior: edit
  `templates/deployment.yaml`
- change naming or the Service-name helper other charts call into: edit
  `templates/_helpers.tpl`
- add or change a self-contained validation rule: edit
  `templates/validation.yaml`

## Validation

After changing anything here, render this chart as part of the umbrella
(`helm template dlh charts/dlh-in-a-box -f examples/values-dev.yaml`, or any
other example values file with `cloudbeaver.enabled: true`) and confirm the
expected Service/Deployment/ConfigMap render, then run the umbrella's
`test/render-contract.sh`.
