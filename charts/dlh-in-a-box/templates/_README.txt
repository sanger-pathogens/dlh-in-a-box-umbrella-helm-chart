# Umbrella Templates

This folder contains the Helm render files that are owned by this repo.

A template is a file that turns chart settings into Kubernetes YAML.

If a behavior is specific to `dlh-in-a-box`, it usually lives here instead of
inside an upstream chart.

## What this folder does

```mermaid
flowchart LR
  Values[Chart settings] --> Validation[Validation files]
  Validation --> Resources[Rendered Kubernetes YAML]
  Resources --> Apps[Running apps]
```

## File map

| File | Plain meaning |
| --- | --- |
| `_helpers.tpl` | Shared naming and helper functions |
| `_ranger-admin.tpl` | Shared Ranger admin helper logic |
| `identity-validation.yaml` | Blocks unsupported sign-in combinations |
| `governance-validation.yaml` | Blocks incomplete or unsafe governed-data settings |
| `platform-home.yaml` | Renders the optional browser home page |
| `cloudbeaver.yaml` | Renders CloudBeaver and its extra config |
| `ranger-admin.yaml` | Renders Ranger Admin pieces |
| `ranger-automation.yaml` | Creates Ranger roles, policies, and sync jobs |
| `ranger-browser-proxy.yaml` | Renders the optional Ranger browser proxy |
| `datahub-auth-secrets.yaml` | Creates small helper Secrets for DataHub auth |
| `datahub-prerequisites-compat.yaml` | Adds compatibility resources for DataHub prerequisites |
| `NOTES.txt` | The text Helm prints after install |

## When you can ignore this folder

You can ignore this folder if you only want to install the chart.

You need this folder when you are changing chart render logic.

## Common mistake

Do not put umbrella-specific logic into an upstream dependency chart when it
really belongs here.
