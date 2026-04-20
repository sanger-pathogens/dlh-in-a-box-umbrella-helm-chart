# Glossary

This page explains the words used in the docs in the simplest way possible.

## Core Platform Terms

- `Kubernetes`
  The system that runs containers in a cluster.
- `Helm`
  A tool used to install apps on Kubernetes.
- `Helm chart`
  A reusable install package for Kubernetes.
- `Umbrella chart`
  One chart that installs several other tools together.
- `Consumer repository`
  Another repository that uses this chart and adds environment-specific config.
- `Example overlay`
  A YAML file in [`../examples/`](../examples/) that shows one way to configure
  the chart.
- `platformHome`
  An optional home page for users in the browser.

## Identity And Access Terms

- `Identity`
  Who the user is.
- `Authentication`
  How the system checks who the user is.
- `Authorization`
  What the user is allowed to do.
- `Keycloak`
  The login system used in the shared examples in this repository.
- `OIDC`
  The browser login standard used by Keycloak and several apps in this chart.
- `LDAP`
  A directory service that stores users and groups.
- `Active Directory`
  Microsoft’s directory service. In this project, it is treated as one kind of
  LDAP directory.
- `LDAPS`
  LDAP over TLS. In simple terms: LDAP with encryption.
- `externalLdap`
  The mode where Keycloak handles sign-in, but users and groups still come from
  LDAP or Active Directory.
- `keycloakLocal`
  The mode where Keycloak stores users itself instead of reading them from LDAP.
- `Group`
  A named set of users.
- `Principal`
  The username or identity the app sees after login.

## Authorization Terms

- `Ranger`
  The tool used for access rules and role information.
- `Platform role`
  A named bundle of access rules in the chart.
- `Exception role`
  A temporary extra access rule for one person or case.
- `bootstrapPolicies`
  Access rules the chart creates in Ranger from the values file.
- `authorizedGroups`
  An older, simpler access-list input still supported for migration.

## Data Terms

- `Catalog`
  A named data source in Trino.
- `Governance metadata`
  The required information that says what kind of data a catalog contains and
  why it is allowed on the platform.
- `Classification`
  The sensitivity level of the data, such as private or public.
- `Owner PI`
  The person who is accountable for the dataset.
- `Data steward`
  The person or team who looks after the dataset day to day.
- `Approval reference`
  The record that says the dataset is allowed on the platform.

## Application Terms

- `Trino`
  The SQL engine people use to query data.
- `Hive Metastore`
  The service that stores table metadata.
- `Prefect`
  The workflow tool.
- `CloudBeaver`
  The browser SQL tool.
- `JupyterHub`
  The notebook server.
- `DataHub`
  The metadata catalog.
- `Smoke install`
  A scripted local test install that proves the auth-enabled example really works.
