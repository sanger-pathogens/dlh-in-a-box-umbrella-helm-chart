# Chart File Payloads

This folder contains static files that the chart copies into rendered runtime
objects.

## What Lives In This Folder

| Path | Ownership | What it is for |
| --- | --- | --- |
| `platform-home/` | repo-owned | static browser asset payloads used by the optional launchpad |
| `ranger-automation/` | repo-owned | Python run by the Ranger bootstrap and Keycloak user-sync jobs |
| `prefect/` | repo-owned | base job template handed to the Prefect worker |
| `datahub-group-role-sync/` | repo-owned | the DataHub Actions plugin that turns OIDC-provisioned group membership into DataHub Admin/Editor/Reader assignments |
| `README.md` | repo-owned guide | explains why the folder is small and what belongs here |

The chart uses `files/` only for assets that need to be copied verbatim into a
rendered object.

The important distinction is:

- `files/` is for payload files such as browser adapters
- `templates/` is for behavior, control flow, and runtime code generation


## Validation

After changing files in this folder, run:

```commandline
make template
```

Use the local auth smoke install when you changed a browser asset that could
affect actual login flow.

```commandline
make smoke-install
```

## Common Mistakes

- putting values-aware logic in `files/` when it belongs in a template
