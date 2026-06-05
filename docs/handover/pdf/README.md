# PDF Handover Deck Exports

This folder contains PDF exports of the handover decks for presentation and sharing.

```mermaid
flowchart TD
  Specs[session specs] --> Html[HTML slide render]
  Html --> Pdf[PDF exports]
  Pdf --> Delivery[presenter handout]
```

The PDFs are regenerated from the same session specifications as the PPTX files.
