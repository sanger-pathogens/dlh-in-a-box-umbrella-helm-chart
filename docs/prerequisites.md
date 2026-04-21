# Prerequisites

This page is for someone who has never used this repository before.

Audience: first-time readers who want the simplest safe starting point.

What you will learn: the basic words used in the docs, what tools you need,
and what this repository does not set up for you.

Read next: [quickstart.md](quickstart.md).

## What This Repository Does Not Do For You

Before you try the quickstart, know these limits:

- this repository does not create a Kubernetes cluster
- this repository does not create your real DNS names or TLS certificates
- this repository does not create your real production secrets
- this repository does not decide your organization's access policy

If you do not already have a Kubernetes cluster you can install into, stop
here and set that up first.

## Basic Words

These are the main words used throughout the docs:

| Word | Plain meaning |
| --- | --- |
| `Kubernetes` | The system that runs apps in a cluster. |
| `cluster` | The Kubernetes environment where your apps run. |
| `namespace` | A folder-like space inside the cluster. |
| `Helm` | A tool for installing apps on Kubernetes. |
| `Helm chart` | The install package Helm uses. |
| `values file` | A YAML file that tells the chart what to turn on and how to configure it. |
| `overlay` | An example values file you start from or copy from. |

## What You Need For The Simplest Local Install

To follow the happy-path quickstart, you need:

- a clone of this repository
- `kubectl`
- `helm`
- a working Kubernetes cluster you can reach with `kubectl`
- permission to create a namespace and install workloads in that cluster

This repository does not care which Kubernetes distribution you use for the
local path. `kind`, `minikube`, `k3d`, or an existing cluster can all work as
long as Helm and `kubectl` can talk to it.

## What Maintainers Usually Need In Addition

If you are maintaining the repository rather than just trying the chart, you
will usually also need:

- Docker for full Mermaid diagram validation in `./hack/docs-check.sh`
- a cluster suitable for running `make smoke-install`
- enough permissions to create demo Secrets in the target namespace

## Preflight Checks

Run these commands before the quickstart:

```bash
kubectl config current-context
kubectl get nodes
helm version
```

If one of those commands fails, the quickstart will fail too.

## Choose The Right First Path

- If you want the simplest possible first install, use
  [`../examples/values-local.yaml`](../examples/values-local.yaml).
- If you want the auth-enabled smoke path later, use
  [`../examples/values-local-auth.yaml`](../examples/values-local-auth.yaml)
  through `make smoke-install`, not as your first manual install.
- If you need a deeper explanation before you install anything, read
  [../charts/dlh-in-a-box/README.md](../charts/dlh-in-a-box/README.md).
