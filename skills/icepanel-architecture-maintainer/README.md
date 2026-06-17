# IcePanel Architecture Maintainer Skill

This skill covers the architecture model and exported diagrams.

Read [SKILL.md](SKILL.md) when changing the IcePanel model, validating
architecture JSON, exporting diagrams, or updating architecture image/PDF
artifacts.

```mermaid
flowchart TD
  ArchitectureChange[architecture change]
  Skill[SKILL.md]
  Model[IcePanel model]
  Validate[validate JSON]
  Export[export diagrams]
  Docs[architecture docs]

  ArchitectureChange --> Skill
  Skill --> Model
  Model --> Validate
  Validate --> Export
  Export --> Docs
```

## Files

| Path | What it is for |
| --- | --- |
| `README.md` | this folder guide |
| `SKILL.md` | reusable IcePanel architecture maintenance procedure |
