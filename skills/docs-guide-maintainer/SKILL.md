---
name: docs-guide-maintainer
description: Use when adding or editing repository guides, README/OVERVIEW files, Mermaid diagrams, local documentation links, docs-check behavior, or new directories that need guide files in this repository.
---

# Docs Guide Maintainer Skill

Use this skill for documentation changes that must satisfy the repo's
README-first guide system.

## Repo Documentation Model

- The root `README.md` is the newcomer entry point.
- Explanations should live near the code or folder they describe.
- `docs/` is intentionally small and holds shared support material.
- `.github/OVERVIEW.md` exists to avoid GitHub surfacing a workflow-folder
  README as the repository home page.
- `docs/Internal/` is excluded from the public guide-file contract.

## Directory Guide Rule

Most directories need one of:

- `README.md`
- `OVERVIEW.md`
- `_README.txt`
- `README.md.gotmpl`

Each guide file, except `.gotmpl`, must include a Mermaid block.

When adding a directory, add the guide in the same change. For new skill
folders, use:

- `skills/<name>/README.md`
- `skills/<name>/SKILL.md`

## Mermaid Blocks

Keep Mermaid diagrams small and structural. They should help readers navigate,
not duplicate every paragraph.

Local development can skip render validation:

```bash
SKIP_MERMAID_CHECK=1 ./scripts/docs-check.sh
```

CI or strict local checks may require Docker for Mermaid rendering.

## Links

Use relative links for files in the repo. After moving files, run docs-check to
catch broken local links.

When linking from docs to skills, keep one source of truth. Prefer a short docs
pointer to duplicating a long workflow.

## Common Tasks

Adding a new guide:

1. Create the guide in the folder being described.
2. Add a compact Mermaid diagram.
3. Link it from the closest index guide only if it helps navigation.
4. Run docs-check.

Moving documentation:

1. Move the authoritative content.
2. Leave a pointer only when old paths are likely to be used.
3. Update local links.
4. Run docs-check.

Editing workflow docs:

1. Keep `.github/workflows/README.md` aligned with actual workflow YAML.
2. Keep `scripts/README.md` aligned with local scripts.
3. Do not describe a CI behavior that no local script can reproduce unless the
   workflow truly adds behavior.

## Validation

Run:

```bash
SKIP_MERMAID_CHECK=1 ./scripts/docs-check.sh
```

If Docker is available and the change is Mermaid-heavy, also run:

```bash
./scripts/docs-check.sh
```
