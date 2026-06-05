# Editable Handover PPTX Decks

This folder contains editable PowerPoint versions of the generated handover decks.

```mermaid
flowchart TD
  Specs[session specs] --> PptxGen[PptxGenJS export]
  PptxGen --> Decks[editable PPTX files]
  Decks --> Notes[speaker notes]
```

Use these files when a maintainer needs to revise slide text, speaker notes, or deck order.
