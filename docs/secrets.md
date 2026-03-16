# Secrets

## Why Vault is included

Vault is included as a platform component so the umbrella deployment has a clear, central secrets management option from day one.

## How to handle secrets

- Do **not** place real secrets in tracked Helm values files.
- Prefer externally managed Kubernetes secrets and reference them from chart values.
- Use Vault (in-cluster or external) as the long-term system of record for secrets.

## What not to commit

Do not commit:

- object storage access keys
- database passwords
- API tokens
- TLS private keys

## Referencing existing secrets

For storage and other integrations, set values to reference pre-created secrets (for example `global.storage.existingSecret`) and keep secret creation in secure workflows outside of this repository.

## External Vault option

If your organization already runs Vault, disable the in-chart dependency:

```yaml
vault:
  enabled: false
```

Then integrate workloads with your existing Vault deployment approach.
