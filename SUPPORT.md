# Support

This file explains what kind of help fits this repo.

## What support is a good fit for

- chart installation and upgrade questions
- example settings file usage
- chart setting questions
- GHCR consumption from downstream repositories
- local validation, including the difference between manual local install and
  the auth-enabled smoke path
- unexpected behavior in the umbrella chart or its chart-owned glue logic

## What is usually out of scope

- custom pipeline or application code in downstream repositories
- cluster bootstrap decisions outside this chart
- institution-specific platform decisions that belong in the downstream repo
- purely upstream bugs that need to be fixed in the original project first

## How to ask for help

Use the repository issue templates when appropriate and include:

- the chart version or commit SHA
- the example file or settings fragment involved
- whether you used `examples/values-local.yaml`,
  `examples/values-local-auth.yaml`, or another example file
- whether you ran a manual install or `make smoke-install`
- the Kubernetes distribution and version
- the exact error or unexpected behavior
- the commands you already ran

For sensitive issues:

- use [SECURITY.md](SECURITY.md) for security concerns
- do not post secrets, tokens, private hostnames, or private infrastructure details in public

## Governance note

This repository may be publicly visible while pull requests remain limited to
repository collaborators. Public visibility supports reuse and consumption;
support responses are still handled on a best-effort basis by the maintainers.
