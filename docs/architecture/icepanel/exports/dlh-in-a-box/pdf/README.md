# DLH-in-a-box PDF Diagram Bundle

This folder contains the combined PDF export for the `dlh-in-a-box` IcePanel
diagrams.

```mermaid
flowchart TD
  PngExports[PNG diagram exports] --> PdfBuilder[PDF builder]
  PdfBuilder --> Bundle[dlh-in-a-box-diagrams.pdf]
  Bundle --> Reviewers[architecture reviewers]
  Bundle --> Publications[publication drafts]
```

## Files

| File | Purpose |
| --- | --- |
| [dlh-in-a-box-diagrams.pdf](dlh-in-a-box-diagrams.pdf) | Combined diagram bundle for review and document inclusion. |

## Maintenance

Regenerate this file from the PNG export set when diagrams change. The PDF is a
derived artifact and should stay consistent with the sibling PNG folders.
