---
name: chart-contract-maintainer
description: Use when changing Helm chart values, values.schema.json, validation templates, render-contract assertions or fixtures, example overlays, or expected rendered manifests in this repository.
---

# Chart Contract Maintainer Skill

Use this skill when work touches chart behavior or the safety contract around
chart values.

## Core Files

- `charts/dlh-in-a-box/values.yaml`
- `charts/dlh-in-a-box/values.schema.json`
- `charts/dlh-in-a-box/templates/*-validation.yaml`
- `charts/dlh-in-a-box/templates/*.yaml`
- `examples/*.yaml`
- `test/render-contract.sh`
- `test/render-contract/*.yaml`
- `test/render-contract/README.md`
- `charts/dlh-in-a-box/README.md`
- `charts/dlh-in-a-box/templates/_README.txt`

## Workflow

1. Identify the contract being changed:
   - default value
   - schema validation
   - template rendering
   - explicit chart failure
   - example overlay behavior
2. Update the smallest owning source file first.
3. Keep schema, defaults, templates, examples, and docs aligned.
4. Add or update render-contract coverage before trusting the change.
5. Run the local validation gate.

## Render Contract Patterns

Use positive renders for supported behavior:

- base chart
- `examples/values-local-auth.yaml`
- `examples/values-dev.yaml`
- `examples/values-prod.yaml`
- focused fixture overlays from `test/render-contract/`

Use negative fixtures for rejected behavior:

- one fixture per invalid scenario
- short fixture names that describe the failure
- expected failure text in `test/render-contract.sh`
- fixture description in `test/render-contract/README.md`

Prefer `expect_fail_any` when Helm schema wording differs across tool versions.
Use exact `expect_fail` for chart-authored validation messages.

## Validation Message Drift

If `scripts/verify.sh` fails because expected failure text no longer matches:

1. Inspect the actual failure output.
2. Inspect the corresponding validation template.
3. Decide whether chart behavior or test text is stale.
4. Patch the source of truth, not only the test.
5. Update fixture README wording when the behavior changed.

Do not weaken a contract just to make CI pass.

## Schema Rules

When adding values:

- add defaults to `values.yaml`
- add schema shape and restrictions to `values.schema.json`
- update examples if the value matters for supported overlays
- update docs if users or maintainers need to understand the value

When deprecating values:

- keep a chart-authored validation error when possible
- add a negative render-contract fixture
- give the replacement path in the error message

## Local Checks

Run from repo root:

```bash
./scripts/render-contract.sh
./scripts/verify.sh
./scripts/template.sh
```

For package-impacting changes, also run:

```bash
./scripts/helm-dependency-update.sh
rm -rf dist
./scripts/package.sh
```

If a single overlay fails, isolate it:

```bash
helm template dlh charts/dlh-in-a-box -f examples/values-dev.yaml --debug
```
