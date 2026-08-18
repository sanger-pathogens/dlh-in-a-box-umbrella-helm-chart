# DLH-in-a-box Architecture Model

This folder contains the IcePanel model for the `dlh-in-a-box` umbrella Helm
chart and the publication-facing companion description.

The canonical model source is:

```text
docs/architecture/icepanel/models/dlh-in-a-box.json
```

Use the Markdown file as explanatory documentation for reviewers and article
authors. Do not treat it as the sync source of truth.

## Files

| Path | Purpose |
| --- | --- |
| `icepanel/models/dlh-in-a-box.json` | Canonical IcePanel-as-code model source. |
| `icepanel/models/dlh-in-a-box.schema.json` | JSON schema for the model file. |
| `dlh-in-a-box-icepanel-model.md` | Publication-readable companion model description. |
| `local-kubernetes-docker-deployment.puml` | PlantUML deployment diagram for a laptop install using Docker, kind, Kubernetes, and Helm. |
| `icepanel/exports/dlh-in-a-box/png-dark/` | Exported dark-mode PNG files for the official diagrams. |

## IcePanel Group Rule

IcePanel groups must contain their member objects in the model. Do not only
draw a visual group around objects on the canvas. The JSON `groups` field is
used by `sync_dlh_icepanel.py` to set IcePanel `groupIds`, so each grouped item
is actually assigned to the group in IcePanel.

## Reality Links

Objects that correspond to repository content use the JSON `links` field to
point at GitHub `main` branch files or folders. The sync script translates those
URLs into IcePanel reality links by using IcePanel's URL resolver.
