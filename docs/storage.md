# Storage

## Default model: external S3-compatible storage

The chart defaults to:

```yaml
global:
  storage:
    backend: externalS3
```

This enables teams to use managed object stores (AWS S3, MinIO external, Ceph RGW, etc.) without coupling storage lifecycle to the cluster.

## Optional mode: in-cluster MinIO

Set:

```yaml
minio:
  enabled: true
global:
  storage:
    backend: minio
```

Use this for development or constrained setups where managed object storage is not available.

## Secret handling

- Prefer `global.storage.existingSecret` to reference an existing Kubernetes secret.
- If no existing secret is provided and `backend=externalS3`, a minimal placeholder secret template is rendered to normalize config keys.
- Never commit real access keys in values files.
