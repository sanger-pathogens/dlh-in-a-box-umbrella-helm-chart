# DLH-in-a-box Light PNG Diagrams

This folder contains light-mode PNG exports for the official `dlh-in-a-box`
IcePanel diagrams.

```mermaid
flowchart TD
  Model[IcePanel model] --> LightExport[light-mode export]
  LightExport --> NumberedPngs[numbered PNG files]
  NumberedPngs --> Documents[light-background documents]
  NumberedPngs --> Comparisons[diagram review comparisons]
```

## Files

The numbered PNG files correspond to the official IcePanel diagram order. Keep
the filenames stable unless the model diagram sequence changes intentionally.

## Maintenance

Use these images where a light document background is preferred. Regenerate the
full set together so the light and dark export folders stay aligned.
