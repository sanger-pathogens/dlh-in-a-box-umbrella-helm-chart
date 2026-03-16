# Environments

## Overlay strategy

Use a base values file (`charts/dlh-in-a-box/values.yaml`) and layer environment-specific files in deployment workflows:

- dev: small footprint, optional components off
- prod: stronger defaults, explicit external dependencies
- scenario overlays: storage-specific switches (external S3 vs MinIO)

## Development example

`examples/values-dev.yaml`:

- external S3 default
- DataHub disabled
- Hive disabled
- minimal worker replicas

## Production baseline

`examples/values-prod.yaml`:

- external S3 default
- Vault enabled
- MinIO disabled
- worker replicas increased

## MinIO-enabled scenario

`examples/values-minio.yaml` enables MinIO and switches storage backend to `minio`.

## Applying overlays

```bash
helm upgrade --install dlh charts/dlh-in-a-box \
  -f charts/dlh-in-a-box/values.yaml \
  -f examples/values-prod.yaml
```
