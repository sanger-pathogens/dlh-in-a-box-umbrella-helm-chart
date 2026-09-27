# Maintainer Skills

This folder contains reusable, agent-neutral operating procedures for this
repository.

Use these skills when a maintainer or assistant needs a repeatable workflow
that is more procedural than ordinary documentation.

```mermaid
flowchart TD
  subgraph Skills["skills/"]
    SkillsGuide[skills/README.md]
    CiSkill[helm-ci-stabilizer]
    IdentitySkill[identity-access-maintainer]
  end

  subgraph Workflows["Repeated workflows"]
    Validate[local validation]
    Tag[tagged commit]
    GitHubRelease[GitHub Release]
    Publish[Helm Publish]
    Zenodo[Zenodo DOI]
    Access[identity and access]
  end

  SkillsGuide --> ReleaseSkill
  SkillsGuide --> CiSkill
  SkillsGuide --> IdentitySkill
  ReleaseSkill --> Validate
  ReleaseSkill --> Tag
  ReleaseSkill --> GitHubRelease
  ReleaseSkill --> Publish
  ReleaseSkill --> Zenodo
  CiSkill --> Validate
  IdentitySkill --> Access
```

## What Lives Here

| Path | What it is for |
| --- | --- |
| `README.md` | explains the purpose of the shared skills folder |
| `identity-access-maintainer/` | Keycloak, Ranger, oauth2-proxy, platform-home, app access, and governance access changes |
| `release-agent/` | tagged Helm chart releases, GitHub Releases, GHCR publishing, Zenodo DOI metadata, and badges |

## Skill Format

Skills in this folder are Markdown and intentionally agent-neutral. They are
not tied to Codex, Claude, or any other specific assistant runtime.

Each skill folder should include:

- `README.md` as the folder guide
- `SKILL.md` as the reusable procedure, with optional YAML frontmatter that
  helps agents route to the skill

## Validation

If you add or edit skills, run:

```bash
SKIP_MERMAID_CHECK=1 ./scripts/docs-check.sh
```
