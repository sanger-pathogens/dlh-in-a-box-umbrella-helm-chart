# Support

This repository publishes and documents the `dlh-in-a-box` Helm chart. Support
is focused on helping consumers understand, deploy, and operate that chart.

## What support is a good fit for

- installation and upgrade questions
- chart values and overlay usage
- GHCR consumption from sibling repositories
- local validation and kind-based testing
- unexpected behavior in the umbrella chart or its locally owned composition logic

## What is usually out of scope

- custom pipeline or application code in consumer repositories
- organization-specific platform decisions outside the chart itself
- upstream product issues that need to be fixed in the original project first

## How to ask for help

Use the repository issue templates when appropriate and include:

- the chart version or commit SHA
- the values file or relevant configuration fragment
- the Kubernetes distribution and version
- the exact failure or unexpected behavior
- the commands you already ran, including validation steps if relevant

For sensitive issues:

- use [SECURITY.md](SECURITY.md) for security concerns
- avoid posting secrets, tokens, or private infrastructure details in public

## Governance note

This repository may be publicly visible while pull requests remain limited to
repository collaborators. Public visibility is intended to support reuse and
consumption; support responses are still handled on a best-effort basis by the
maintainers.
