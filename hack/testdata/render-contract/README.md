# Render Contract Fixtures

These values overlays are intentionally small and often intentionally invalid.

`hack/render-contract.sh` layers them on top of the main example files to
prove that the chart accepts the supported contract and rejects unsafe or
stale configurations.

The negative fixtures deliberately cover:

- missing governance and auth requirements
- missing explicit environment selection for shared identity or governed catalogs
- wildcard OIDC client settings outside local mode
- missing Prefect group restrictions
- missing CloudBeaver group restrictions
- missing portal redirect URIs
- missing CloudBeaver proxy secret wiring
- stale top-level auth blocks and legacy Trino auth toggles
