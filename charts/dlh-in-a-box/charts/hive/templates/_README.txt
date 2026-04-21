# Hive Templates

This folder contains the render files for the local Hive subchart.

A template is a file that turns chart settings into Kubernetes YAML.

## Template flow

```mermaid
flowchart LR
  Settings[Hive settings] --> Templates[Template files]
  Templates --> YAML[Rendered Kubernetes YAML]
  YAML --> Hive[Running Hive resources]
```

## File map

| File | Plain meaning |
| --- | --- |
| `_helpers.tpl` | Naming and catalog helper logic |
| `configmap.yaml` | Per-catalog Hive config files |
| `init-config.yaml` | Bootstrap config used during init |
| `init-schema-job.yaml` | Optional schema setup job |
| `metastore.yaml` | Per-catalog Service, Deployment, and optional Ingress resources |
| `postgres-secret.yaml` | Creates a PostgreSQL Secret when you did not supply one |
| `s3-secret.yaml` | Creates a storage Secret when you did not supply one |

## When you can ignore this folder

You can ignore this folder unless you are changing the Hive subchart.

## Common mistake

`metastore.yaml` is the main file here. Changes to Hive startup, mounts, or
ingress usually land there and should be tested with a real example file.
