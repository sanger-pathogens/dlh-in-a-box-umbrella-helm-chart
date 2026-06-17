---
name: icepanel-architecture-maintainer
description: Use when editing the repository architecture model, IcePanel JSON, exported architecture diagrams, architecture PDFs, or related docs under docs/architecture in this repository.
---

# IcePanel Architecture Maintainer Skill

Use this skill for architecture model and diagram work under `docs/architecture`.

## Core Files

- `docs/architecture/README.md`
- `docs/architecture/dlh-in-a-box-icepanel-model.md`
- `docs/architecture/icepanel/models/dlh-in-a-box.json`
- `docs/architecture/icepanel/models/dlh-in-a-box.schema.json`
- `docs/architecture/icepanel/exports/dlh-in-a-box/`
- `docs/architecture/validate_dlh_icepanel_json.py`
- `docs/architecture/export_dlh_icepanel_diagrams.py`
- `docs/architecture/png_diagram_pdf.py`
- `docs/architecture/sync_dlh_icepanel.py`

## Workflow

1. Inspect the existing model and exports before editing.
2. Update the source model rather than hand-editing generated exports.
3. Validate the IcePanel JSON against the schema.
4. Regenerate exports with the repo scripts.
5. Update README or companion docs when diagram meaning changes.
6. Run docs validation.

## Commands

Start with:

```bash
python3 docs/architecture/validate_dlh_icepanel_json.py
```

Inspect script arguments before running export or sync scripts:

```bash
python3 docs/architecture/export_dlh_icepanel_diagrams.py --help
python3 docs/architecture/png_diagram_pdf.py --help
python3 docs/architecture/sync_dlh_icepanel.py --help
```

Then run only the export path needed for the change. Avoid regenerating large
binary artifacts unless the source model changed.

## Export Discipline

- Keep light and dark PNG exports aligned when both are expected.
- Keep exported PDF artifacts aligned with PNG exports when the PDF is part of
  the published documentation path.
- Do not manually edit generated PNG or PDF files.
- Check binary churn before committing. If many exports changed, confirm the
  model change justifies the churn.

## Validation

Run:

```bash
python3 docs/architecture/validate_dlh_icepanel_json.py
SKIP_MERMAID_CHECK=1 ./hack/docs-check.sh
```

If architecture diagrams were regenerated, inspect at least a sample of the
changed images before committing.
