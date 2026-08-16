# Maintainer Skills

This folder contains reusable, agent-neutral operating procedures for this
repository.

Use these skills when a maintainer or assistant needs a repeatable workflow
that is more procedural than ordinary documentation.

```mermaid
flowchart TD
  subgraph Skills["skills/"]
    SkillsGuide[skills/README.md]
    ReleaseSkill[release-agent]
    CiSkill[helm-ci-stabilizer]
    ContractSkill[chart-contract-maintainer]
    IdentitySkill[identity-access-maintainer]
    DocsSkill[docs-guide-maintainer]
    ArchitectureSkill[icepanel-architecture-maintainer]
  end

  subgraph Workflows["Repeated workflows"]
    Validate[local validation]
    Tag[tagged commit]
    GitHubRelease[GitHub Release]
    Publish[Helm Publish]
    Zenodo[Zenodo DOI]
    Contract[render contracts]
    Access[identity and access]
    Docs[folder guides]
    Diagrams[architecture exports]
  end

  SkillsGuide --> ReleaseSkill
  SkillsGuide --> CiSkill
  SkillsGuide --> ContractSkill
  SkillsGuide --> IdentitySkill
  SkillsGuide --> DocsSkill
  SkillsGuide --> ArchitectureSkill
  ReleaseSkill --> Validate
  ReleaseSkill --> Tag
  ReleaseSkill --> GitHubRelease
  ReleaseSkill --> Publish
  ReleaseSkill --> Zenodo
  CiSkill --> Validate
  ContractSkill --> Contract
  IdentitySkill --> Access
  DocsSkill --> Docs
  ArchitectureSkill --> Diagrams
```

## What Lives Here

| Path | What it is for |
| --- | --- |
| `README.md` | explains the purpose of the shared skills folder |
| `chart-contract-maintainer/` | chart validation, values schema, render-contract fixtures, and example render coverage |
| `docs-guide-maintainer/` | README-first folder guides, Mermaid blocks, local links, and docs-check behavior |
| `helm-ci-stabilizer/` | Helm Lint, Helm Publish, smoke workflow, dependency-update, and GHCR CI failures |
| `icepanel-architecture-maintainer/` | IcePanel model maintenance, validation, diagram export, and derived architecture artifacts |
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
