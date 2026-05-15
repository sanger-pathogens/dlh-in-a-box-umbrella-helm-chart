# Handover Deck Assets

This folder contains generated and reused raster assets for the handover decks.

```mermaid
flowchart TD
  Markdown[Mermaid blocks in repo docs] --> Rendered[mermaid PNG assets]
  IcePanel[IcePanel PNG exports] --> Decks[handover decks]
  Rendered --> Decks
```

The source IcePanel PNGs remain under [../../architecture/icepanel/exports/](../../architecture/icepanel/exports/).
