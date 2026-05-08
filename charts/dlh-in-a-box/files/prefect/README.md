# Prefect File Payloads

This folder contains static Prefect payloads that the chart copies into
rendered runtime objects.

```mermaid
flowchart TD
  TemplateFile[kubernetes base job template] --> Chart[Helm chart files]
  Chart --> Rendered[rendered Prefect worker config]
  Rendered --> Jobs[Prefect Kubernetes jobs]
```

## What Lives Here

| File | What it is for |
| --- | --- |
| `kubernetes-base-job-template.json` | base Kubernetes job template used by Prefect workers |
