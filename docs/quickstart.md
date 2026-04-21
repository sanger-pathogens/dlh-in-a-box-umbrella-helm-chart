# Quickstart

This page is the one true happy-path tutorial for a first local install.

Audience: someone who wants the simplest possible first success.

What you will learn: how to install the chart locally with
`examples/values-local.yaml`, how to tell whether it worked, and what to try
next.

Read next: [../examples/README.md](../examples/README.md) if you need a
different overlay after this tutorial.

## 1. Before You Start

Read [prerequisites.md](prerequisites.md) first.

This quickstart assumes:

- `kubectl` works against a real Kubernetes cluster
- `helm` is installed
- you are running commands from the repository root

## 2. Install The Chart Dependencies

Run:

```bash
./hack/helm-dependency-update.sh
```

This downloads the packaged chart dependencies that the umbrella chart needs.

## 3. Install The Simplest Local Overlay

Run:

```bash
helm upgrade --install dlh charts/dlh-in-a-box \
  -n data-lakehouse-local \
  --create-namespace \
  -f examples/values-local.yaml
```

Why this is the recommended first path:

- it is the simplest tracked example
- it does not rely on pre-seeded demo Secrets
- it is the easiest way to prove the chart can install in your cluster

## 4. Check That It Worked

Run:

```bash
kubectl get pods -n data-lakehouse-local
kubectl get svc -n data-lakehouse-local
```

What success looks like:

- most pods are `Running`
- one-off setup jobs may be `Completed`
- services such as `dlh-trino`, `prefect-server`, `dlh-minio`, and
  `dlh-vault` exist in the namespace

If the namespace is empty or many pods are stuck in `Pending`, the install did
not complete successfully.

## 5. Open A Few Local Endpoints

Run each port-forward command in its own terminal.

Trino UI:

```bash
kubectl port-forward -n data-lakehouse-local svc/dlh-trino 8080:8080
```

Then open `http://localhost:8080/ui/`.

Prefect UI:

```bash
kubectl port-forward -n data-lakehouse-local svc/prefect-server 4200:4200
```

Then open `http://localhost:4200`.

MinIO console:

```bash
kubectl port-forward -n data-lakehouse-local svc/dlh-minio 9001:9001
```

Then open `http://localhost:9001`.

The tracked local overlay uses the demo MinIO credentials from
[`../examples/values-local.yaml`](../examples/values-local.yaml):

- username: `minioadmin`
- password: `minioadmin123`

## 6. Clean Up When You Are Done

Run:

```bash
helm uninstall dlh -n data-lakehouse-local
kubectl delete namespace data-lakehouse-local
```

## 7. If You Need The Auth-Enabled Path Next

Do not use `examples/values-local-auth.yaml` as your first manual install.

That overlay expects demo Kubernetes Secrets to exist first. The normal way to
run it is:

```bash
make smoke-install
```

Or, in script form:

```bash
./hack/smoke-install.sh charts/dlh-in-a-box examples/values-local-auth.yaml
```

Use that path when you want to exercise login, browser proxies, Ranger, and
other auth-related pieces.

## 8. What To Read Next

- want to choose a different example:
  [../examples/README.md](../examples/README.md)
- want to understand the chart itself:
  [../charts/dlh-in-a-box/README.md](../charts/dlh-in-a-box/README.md)
- want to understand login and access:
  [auth-architecture.md](auth-architecture.md)
- want to understand governed data rules:
  [data-governance.md](data-governance.md)
