# Security Policy

## Supported versions

Security fixes are applied on a best-effort basis to the currently maintained
state of this repository:

| Version | Supported |
| --- | --- |
| Latest tagged release | Yes |
| `main` branch | Yes |
| Older tagged releases | No |
| Unreleased feature branches or forks | No |

## Reporting a vulnerability

Please do **not** report security vulnerabilities through public GitHub issues
or pull requests.

Use one of the following private routes instead:

1. GitHub private vulnerability reporting for this repository, if it is enabled
2. A private communication channel to the repository maintainers and code
   owners at the Wellcome Sanger Institute, Parasites and Microbes program,
   Data Engineering and Integration team

Repository ownership is defined in `.github/CODEOWNERS`.

When reporting a vulnerability, please include:

- a clear description of the issue and affected component
- the chart version, commit SHA, or branch where the issue was found
- any relevant configuration or values needed to reproduce it
- impact assessment, if known
- proof-of-concept details only as needed to explain the issue safely

## Disclosure expectations

- Please allow the maintainers reasonable time to investigate and remediate the
  issue before any public disclosure.
- The maintainers may ask for additional detail or reproduction help during the
  triage process.
- Once a fix is available, the maintainers may coordinate release notes or
  disclosure timing with the reporter where appropriate.

## Scope

This repository primarily distributes Helm chart source and templates for a
Kubernetes-based lakehouse control plane. Security reports are most useful when
they relate to:

- this repository's chart templates, values handling, workflows, or packaging
- the way the umbrella chart composes and configures bundled dependencies
- documentation or automation that could lead to insecure deployment defaults

Issues that are purely upstream product vulnerabilities may still be helpful to
report, but they may need to be addressed in the upstream project as well.
