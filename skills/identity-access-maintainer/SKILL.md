---
name: identity-access-maintainer
description: Use when changing Keycloak identity, Ranger authorization, app access roles, oauth2-proxy clients, Platform Home launchers, CloudBeaver/JupyterHub/Prefect/Trino authentication, or data governance access behavior in this repository.
---

# Identity Access Maintainer Skill

Use this skill for changes around identity, browser access, Ranger data access,
catalog governance, and app launch behavior.

## Current Model

- Keycloak realm roles control browser app access.
- Ranger data access belongs under `global.authorization.ranger.dataRoles` and
  explicit Ranger bootstrap policies.
- Deprecated group-based paths should fail with helpful migration messages.
- Browser proxies enforce access through Keycloak client roles.
- Local, dev, prod, and shared-auth overlays exercise different identity modes.

## High-Churn Files

- `charts/dlh-in-a-box/values.yaml`
- `charts/dlh-in-a-box/values.schema.json`
- `charts/dlh-in-a-box/templates/identity-validation.yaml`
- `charts/dlh-in-a-box/templates/governance-validation.yaml`
- `charts/dlh-in-a-box/templates/ranger-automation.yaml`
- `charts/dlh-in-a-box/templates/platform-home.yaml`
- `charts/dlh-in-a-box/templates/cloudbeaver.yaml`
- `charts/dlh-in-a-box/templates/ranger-admin.yaml`
- `charts/dlh-in-a-box/files/ranger-automation/*.py`
- `charts/dlh-in-a-box/files/platform-home/*`
- `examples/values-local-auth.yaml`
- `examples/values-dev.yaml`
- `examples/values-prod.yaml`
- `examples/values-shared-auth.yaml`
- `test/render-contract.sh`
- `test/render-contract/*.yaml`
- `specs/ranger-keycloak-integration.md`

## Workflow

1. Identify which layer owns the change:
   - shared values model
   - schema validation
   - chart validation template
   - rendered Kubernetes resource
   - bundled automation script
   - browser UI or launcher config
2. Update values and schema before templates when adding new knobs.
3. Update validation templates before render fixtures when rejecting old knobs.
4. Update examples for every supported environment affected by the change.
5. Add positive and negative render-contract coverage.
6. Update specs or folder guides for operator-facing behavior.

## Access Model Guardrails

Preserve these invariants unless the user explicitly asks to redesign them:

- do not reintroduce group-based app access as the primary model
- do not put Ranger role mappings back under identity access-model roles
- do not make `authorizedGroups` valid again for catalogs
- keep local Keycloak bootstrap-user behavior separate from organizational LDAP
- keep Trino browser OAuth and password auth behavior explicit per environment
- keep app proxy allowed roles aligned with access model appAccess

## Common Negative Fixtures

Use or extend fixtures under `../../ test/render-contract/` for:

- deprecated `groupRoleMappings`
- deprecated `authorizedGroups`
- invalid app access keys
- platform-home deprecated `requiredGroups`
- oauth2-proxy deprecated `allowedGroups`
- missing governance metadata
- restricted catalog missing fine-grained policy coverage
- Prefect automation or direct-grant client misconfiguration
- keycloak-local mode mixed with LDAP-only behavior

## Validation

Run:

```bash
./hack/render-contract.sh
./hack/lint.sh
./hack/template.sh
```

For smoke-sensitive identity changes, also run or request:

```bash
./hack/smoke-install.sh charts/dlh-in-a-box examples/values-local-auth.yaml
```

Smoke install touches a Kubernetes cluster, so confirm the current context and
available capacity before running it.

## Review Checklist

Before finishing, answer:

- Which environment overlays changed?
- Which old configuration paths now fail, and with what migration message?
- Which new rendered resources or secrets changed?
- Are local-user, LDAP, and external identity modes still separated?
- Did the rendered manifests avoid exposing credentials through ConfigMaps?
