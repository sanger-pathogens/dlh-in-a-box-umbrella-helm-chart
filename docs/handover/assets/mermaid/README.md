# Rendered Mermaid Assets

This folder contains PNG renders of selected Mermaid diagrams from the published documentation surface.

```mermaid
flowchart TD
  SourceDocs[source markdown files] --> Mermaid[Mermaid fences]
  Mermaid --> Browser[Playwright render]
  Browser --> PNG[PNG assets for decks]
```

Do not edit these PNG files by hand. Re-run the handover deck build instead.
