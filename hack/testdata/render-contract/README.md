# Render Contract Fixtures

These files are small YAML fragments layered on top of the main example
overlays by `hack/render-contract.sh`.

Some fixtures are intentionally valid and some are intentionally invalid. The
goal is to prove the chart still accepts the supported contract and still
rejects unsafe or outdated combinations.

## What these fixtures cover

- missing governance or identity requirements
- missing explicit environment selection
- missing required redirect URIs or group restrictions
- invalid Prefect bearer-token settings
- invalid CloudBeaver auth-proxy wiring
- unsupported legacy identity or Trino auth keys
- invalid `keycloakLocal` and usersync combinations
- exception-role metadata validation

## Maintainer note

Keep these fixtures small and single-purpose. Each file should explain one
contract rule, not three at once.
