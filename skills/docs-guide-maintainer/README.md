# Docs Guide Maintainer Skill

This skill covers the README-first documentation system and folder guide checks.

Read [SKILL.md](SKILL.md) when adding directories, moving docs, editing guide
files, changing Mermaid blocks, or fixing `scripts/repo/docs-check.sh` failures.

```mermaid
flowchart TD
  DocsChange[docs or directory change]
  Skill[SKILL.md]
  Guide[folder guide]
  Links[local links]
  Mermaid[Mermaid block]
  Check[docs-check]

  DocsChange --> Skill
  Skill --> Guide
  Guide --> Links
  Guide --> Mermaid
  Links --> Check
  Mermaid --> Check
```

## Files

| Path | What it is for |
| --- | --- |
| `README.md` | this folder guide |
| `SKILL.md` | reusable documentation guide maintenance procedure |
