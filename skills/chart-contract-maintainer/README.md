# Chart Contract Maintainer Skill

This skill covers chart validation contracts, values schema, examples, and
render-contract fixtures.

Read [SKILL.md](SKILL.md) when changing chart values, validations, rendered
manifest expectations, or example overlays.

```mermaid
flowchart TD
  Change[chart behavior change]
  Skill[SKILL.md]
  Values[values and schema]
  Templates[validation templates]
  Fixtures[render-contract fixtures]
  Checks[lint and template checks]

  Change --> Skill
  Skill --> Values
  Skill --> Templates
  Values --> Fixtures
  Templates --> Fixtures
  Fixtures --> Checks
```

## Files

| Path | What it is for |
| --- | --- |
| `README.md` | this folder guide |
| `SKILL.md` | reusable chart contract maintenance procedure |
