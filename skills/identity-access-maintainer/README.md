# Identity Access Maintainer Skill

This skill covers the repo's repeated identity, access, and governance changes.

Read [SKILL.md](SKILL.md) when changing Keycloak, Ranger, oauth2-proxy,
platform-home launchers, app access, role models, catalog governance, or
browser SSO behavior.

```mermaid
flowchart TD
  Request[identity or access change]
  Skill[SKILL.md]
  Model[access model]
  Templates[chart templates]
  Automation[Ranger automation]
  Examples[example overlays]
  Contracts[render contracts]

  Request --> Skill
  Skill --> Model
  Model --> Templates
  Templates --> Automation
  Templates --> Examples
  Examples --> Contracts
```

## Files

| Path | What it is for |
| --- | --- |
| `README.md` | this folder guide |
| `SKILL.md` | reusable identity and access maintenance procedure |
