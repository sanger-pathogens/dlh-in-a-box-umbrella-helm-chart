{{/* Expand the name of the chart. */}}
{{- define "dlh-in-a-box.name" -}}
{{- default .Chart.Name .Values.global.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Create a default fully qualified app name. */}}
{{- define "dlh-in-a-box.fullname" -}}
{{- if .Values.global.fullnameOverride -}}
{{- .Values.global.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "dlh-in-a-box.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{/* Shared labels */}}
{{- define "dlh-in-a-box.labels" -}}
app.kubernetes.io/name: {{ include "dlh-in-a-box.name" . }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "dlh-in-a-box.keycloak.serviceName" -}}
{{- $keycloak := .Values.keycloak | default dict -}}
{{- if $keycloak.fullnameOverride -}}
{{- $keycloak.fullnameOverride -}}
{{- else -}}
{{- printf "%s-keycloak" .Release.Name -}}
{{- end -}}
{{- end -}}

{{- define "dlh-in-a-box.keycloak.realm" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $provider := get $identity "provider" | default dict -}}
{{- $keycloak := get $provider "keycloak" | default dict -}}
{{- default "dlh" $keycloak.realm -}}
{{- end -}}

{{- define "dlh-in-a-box.keycloak.internalBaseUrl" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $provider := get $identity "provider" | default dict -}}
{{- $keycloak := get $provider "keycloak" | default dict -}}
{{- $scheme := default "http" $keycloak.internalScheme -}}
{{- printf "%s://%s.%s.svc.cluster.local" $scheme (include "dlh-in-a-box.keycloak.serviceName" .) .Release.Namespace -}}
{{- end -}}

{{- define "dlh-in-a-box.keycloak.internalRealmBaseUrl" -}}
{{- printf "%s/realms/%s" (include "dlh-in-a-box.keycloak.internalBaseUrl" .) (include "dlh-in-a-box.keycloak.realm" .) -}}
{{- end -}}

{{- define "dlh-in-a-box.keycloak.browserBaseUrl" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $provider := get $identity "provider" | default dict -}}
{{- $keycloakProvider := get $provider "keycloak" | default dict -}}
{{- $keycloakValues := .Values.keycloak | default dict -}}
{{- $ingress := get $keycloakValues "ingress" | default dict -}}
{{- if $keycloakProvider.browserHost -}}
{{- if regexMatch "^[a-zA-Z][a-zA-Z0-9+.-]*://" $keycloakProvider.browserHost -}}
{{- $keycloakProvider.browserHost -}}
{{- else -}}
{{- printf "https://%s" $keycloakProvider.browserHost -}}
{{- end -}}
{{- else if and (default false $ingress.enabled) $ingress.hostname -}}
{{- printf "%s://%s" (ternary "https" "http" (default false $ingress.tls)) $ingress.hostname -}}
{{- else -}}
{{- include "dlh-in-a-box.keycloak.internalBaseUrl" . -}}
{{- end -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.issuer" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $external := get $identity "external" | default dict -}}
{{- $oidc := get $external "oidc" | default dict -}}
{{- $provider := get $identity "provider" | default dict -}}
{{- if $oidc.issuer -}}
{{- $oidc.issuer -}}
{{- else if eq (default "externalOidc" $provider.mode) "bundledKeycloak" -}}
{{- printf "%s/realms/%s" (include "dlh-in-a-box.keycloak.browserBaseUrl" .) (include "dlh-in-a-box.keycloak.realm" .) -}}
{{- else -}}
{{- "" -}}
{{- end -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.internalIssuer" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $provider := get $identity "provider" | default dict -}}
{{- $providerMode := default "externalOidc" $provider.mode -}}
{{- if eq $providerMode "bundledKeycloak" -}}
{{- include "dlh-in-a-box.keycloak.internalRealmBaseUrl" . -}}
{{- else -}}
{{- include "dlh-in-a-box.identity.issuer" . -}}
{{- end -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.authorizeUrl" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $client := dig "external" "clients" "superset" dict $identity -}}
{{- if $client.authorizeUrl -}}
{{- $client.authorizeUrl -}}
{{- else -}}
{{- printf "%s/protocol/openid-connect/auth" (include "dlh-in-a-box.identity.issuer" .) -}}
{{- end -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.accessTokenUrl" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $client := dig "external" "clients" "superset" dict $identity -}}
{{- if $client.accessTokenUrl -}}
{{- $client.accessTokenUrl -}}
{{- else -}}
{{- printf "%s/protocol/openid-connect/token" (include "dlh-in-a-box.identity.issuer" .) -}}
{{- end -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.internalAccessTokenUrl" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $client := dig "external" "clients" "superset" dict $identity -}}
{{- if $client.internalAccessTokenUrl -}}
{{- $client.internalAccessTokenUrl -}}
{{- else -}}
{{- printf "%s/protocol/openid-connect/token" (include "dlh-in-a-box.identity.internalIssuer" .) -}}
{{- end -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.apiBaseUrl" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $client := dig "external" "clients" "superset" dict $identity -}}
{{- if $client.apiBaseUrl -}}
{{- $client.apiBaseUrl -}}
{{- else -}}
{{- printf "%s/protocol/openid-connect" (include "dlh-in-a-box.identity.issuer" .) -}}
{{- end -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.internalApiBaseUrl" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $client := dig "external" "clients" "superset" dict $identity -}}
{{- if $client.internalApiBaseUrl -}}
{{- $client.internalApiBaseUrl -}}
{{- else -}}
{{- printf "%s/protocol/openid-connect" (include "dlh-in-a-box.identity.internalIssuer" .) -}}
{{- end -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.jwksUri" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $client := dig "external" "clients" "superset" dict $identity -}}
{{- if $client.jwksUri -}}
{{- $client.jwksUri -}}
{{- else -}}
{{- printf "%s/protocol/openid-connect/certs" (include "dlh-in-a-box.identity.issuer" .) -}}
{{- end -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.internalJwksUri" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $client := dig "external" "clients" "superset" dict $identity -}}
{{- if $client.internalJwksUri -}}
{{- $client.internalJwksUri -}}
{{- else -}}
{{- printf "%s/protocol/openid-connect/certs" (include "dlh-in-a-box.identity.internalIssuer" .) -}}
{{- end -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.userInfoUrl" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $client := dig "external" "clients" "superset" dict $identity -}}
{{- if $client.userInfoUrl -}}
{{- $client.userInfoUrl -}}
{{- else -}}
{{- printf "%s/protocol/openid-connect/userinfo" (include "dlh-in-a-box.identity.issuer" .) -}}
{{- end -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.internalUserInfoUrl" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $client := dig "external" "clients" "superset" dict $identity -}}
{{- if $client.internalUserInfoUrl -}}
{{- $client.internalUserInfoUrl -}}
{{- else -}}
{{- printf "%s/protocol/openid-connect/userinfo" (include "dlh-in-a-box.identity.internalIssuer" .) -}}
{{- end -}}
{{- end -}}

{{- define "dlh-in-a-box.platformHome.serviceName" -}}
{{- printf "%s-platform-home" .Release.Name -}}
{{- end -}}

{{- define "dlh-in-a-box.cloudbeaver.serviceName" -}}
{{- printf "%s-cloudbeaver" .Release.Name -}}
{{- end -}}

{{- define "dlh-in-a-box.sharedPostgresql.serviceName" -}}
{{- $sharedPostgresql := .Values.sharedPostgresql | default dict -}}
{{- if $sharedPostgresql.fullnameOverride -}}
{{- $sharedPostgresql.fullnameOverride -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (default "shared-postgresql" $sharedPostgresql.nameOverride) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.directoryMode" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $directory := get $identity "directory" | default dict -}}
{{- default "keycloakLocal" $directory.mode -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.accessModelRolesJson" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $accessModel := get $identity "accessModel" | default dict -}}
{{- $roles := dict -}}
{{- $builtinRoles := get $accessModel "builtinRoles" | default dict -}}
{{- range $roleKey := list "platform-admin" "platform-user" "platform-viewer" -}}
  {{- $role := get $builtinRoles $roleKey | default dict -}}
  {{- $roleEnabled := true -}}
  {{- if hasKey $role "enabled" -}}
    {{- $roleEnabled = get $role "enabled" -}}
  {{- end -}}
  {{- if $roleEnabled -}}
    {{- $_ := set $roles $roleKey $role -}}
  {{- end -}}
{{- end -}}
{{- range $roleKey, $role := get $accessModel "additionalRoles" | default dict -}}
  {{- $roleEnabled := true -}}
  {{- if hasKey $role "enabled" -}}
    {{- $roleEnabled = get $role "enabled" -}}
  {{- end -}}
  {{- if $roleEnabled -}}
    {{- $_ := set $roles $roleKey $role -}}
  {{- end -}}
{{- end -}}
{{- $roles | toJson -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.accessModelAppClientsJson" -}}
{{- $global := .Values.global | default dict -}}
{{- $identity := get $global "identity" | default dict -}}
{{- $external := get $identity "external" | default dict -}}
{{- $clients := get $external "clients" | default dict -}}
{{- $appClients := dict -}}
{{- $superset := get $clients "superset" | default dict -}}
{{- if and (default false (get $superset "enabled")) (get $superset "clientId") -}}
  {{- $_ := set $appClients "superset" $superset.clientId -}}
{{- end -}}
{{- $datahub := get $clients "datahub" | default dict -}}
{{- if and (default false (get $datahub "enabled")) (get $datahub "clientId") -}}
  {{- $_ := set $appClients "datahub" $datahub.clientId -}}
{{- end -}}
{{- $trino := get $clients "trino" | default dict -}}
{{- if and (default false (get $trino "enabled")) (get $trino "clientId") -}}
  {{- $_ := set $appClients "trinoUi" $trino.clientId -}}
{{- end -}}
{{- $jupyterhub := get $clients "jupyterhub" | default dict -}}
{{- if and (default false (get $jupyterhub "enabled")) (get $jupyterhub "clientId") -}}
  {{- $_ := set $appClients "jupyterhub" $jupyterhub.clientId -}}
{{- end -}}
{{- $cloudbeaver := get $clients "cloudbeaverProxy" | default dict -}}
{{- if and (default false (get $cloudbeaver "enabled")) (get $cloudbeaver "clientId") -}}
  {{- $_ := set $appClients "cloudbeaver" $cloudbeaver.clientId -}}
{{- end -}}
{{- $prefect := get $clients "prefectProxy" | default dict -}}
{{- if and (default false (get $prefect "enabled")) (get $prefect "clientId") -}}
  {{- $_ := set $appClients "prefect" $prefect.clientId -}}
{{- end -}}
{{- $ranger := get $clients "rangerProxy" | default dict -}}
{{- if and (default false (get $ranger "enabled")) (get $ranger "clientId") -}}
  {{- $_ := set $appClients "ranger" $ranger.clientId -}}
{{- end -}}
{{- $appClients | toJson -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.keycloakManagedGroupsJson" -}}
{{- list | toJson -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.directory.url" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $directory := get $identity "directory" | default dict -}}
{{- $ldap := get $directory "ldap" | default dict -}}
{{- default "" $ldap.url -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.directory.userBaseDn" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $directory := get $identity "directory" | default dict -}}
{{- $ldap := get $directory "ldap" | default dict -}}
{{- default "" $ldap.userBaseDn -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.directory.groupBaseDn" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $directory := get $identity "directory" | default dict -}}
{{- $ldap := get $directory "ldap" | default dict -}}
{{- default "" $ldap.groupBaseDn -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.directory.bindDn" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $directory := get $identity "directory" | default dict -}}
{{- $ldap := get $directory "ldap" | default dict -}}
{{- default "" $ldap.bindDistinguishedName -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.directory.bindSecretName" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $directory := get $identity "directory" | default dict -}}
{{- $ldap := get $directory "ldap" | default dict -}}
{{- default "" $ldap.bindExistingSecret -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.directory.bindSecretKey" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $directory := get $identity "directory" | default dict -}}
{{- $ldap := get $directory "ldap" | default dict -}}
{{- default "bindPassword" $ldap.bindPasswordKey -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.directory.trustedCaSecretName" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $directory := get $identity "directory" | default dict -}}
{{- $ldap := get $directory "ldap" | default dict -}}
{{- default "" $ldap.trustedCaExistingSecret -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.directory.trustedCaCertKey" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $directory := get $identity "directory" | default dict -}}
{{- $ldap := get $directory "ldap" | default dict -}}
{{- default "ca.crt" $ldap.trustedCaCertKey -}}
{{- end -}}

{{- define "dlh-in-a-box.ranger.admin.serviceName" -}}
{{- printf "%s-ranger-admin" .Release.Name -}}
{{- end -}}

{{- define "dlh-in-a-box.ranger.admin.browserServiceName" -}}
{{- printf "%s-ranger-admin-browser" .Release.Name -}}
{{- end -}}

{{- define "dlh-in-a-box.ranger.browserProxy.serviceName" -}}
{{- printf "%s-ranger-browser-proxy" .Release.Name -}}
{{- end -}}

{{- define "dlh-in-a-box.ranger.admin.url" -}}
{{- printf "http://%s.%s.svc.cluster.local:6080" (include "dlh-in-a-box.ranger.admin.serviceName" .) .Release.Namespace -}}
{{- end -}}

{{- define "dlh-in-a-box.ranger.admin.browserUrl" -}}
{{- printf "http://%s.%s.svc.cluster.local:6080" (include "dlh-in-a-box.ranger.admin.browserServiceName" .) .Release.Namespace -}}
{{- end -}}

{{- define "dlh-in-a-box.ranger.postgresql.serviceName" -}}
{{- printf "%s-ranger-postgresql" .Release.Name -}}
{{- end -}}

{{- define "dlh-in-a-box.trino.serviceName" -}}
{{- printf "%s-trino" .Release.Name -}}
{{- end -}}

{{- define "dlh-in-a-box.ranger.serviceName" -}}
{{- $authorization := .Values.global.authorization | default dict -}}
{{- $ranger := get $authorization "ranger" | default dict -}}
{{- default "trino" $ranger.serviceName -}}
{{- end -}}

{{- define "dlh-in-a-box.ranger.trinoJdbcUrl" -}}
{{- $trino := .Values.trino | default dict -}}
{{- $service := get $trino "service" | default dict -}}
{{- printf "jdbc:trino://%s.%s.svc.cluster.local:%v/system" (include "dlh-in-a-box.trino.serviceName" .) .Release.Namespace (default 8080 $service.port) -}}
{{- end -}}

{{/* Bundled DataHub prerequisites service names */}}
{{- define "dlh-in-a-box.datahubPrerequisites.kafkaService" -}}
{{- printf "%s-kafka" .Release.Name -}}
{{- end -}}

{{- define "dlh-in-a-box.datahubPrerequisites.zookeeperService" -}}
{{- printf "%s-zookeeper" .Release.Name -}}
{{- end -}}

{{- define "dlh-in-a-box.datahubPrerequisites.mysqlService" -}}
{{- printf "%s-mysql" .Release.Name -}}
{{- end -}}

{{- define "dlh-in-a-box.datahubPrerequisites.kafkaFQDN" -}}
{{- printf "%s.%s.svc.cluster.local" (include "dlh-in-a-box.datahubPrerequisites.kafkaService" .) .Release.Namespace -}}
{{- end -}}

{{- define "dlh-in-a-box.datahubPrerequisites.zookeeperFQDN" -}}
{{- printf "%s.%s.svc.cluster.local" (include "dlh-in-a-box.datahubPrerequisites.zookeeperService" .) .Release.Namespace -}}
{{- end -}}

{{- define "dlh-in-a-box.datahubPrerequisites.mysqlFQDN" -}}
{{- printf "%s.%s.svc.cluster.local" (include "dlh-in-a-box.datahubPrerequisites.mysqlService" .) .Release.Namespace -}}
{{- end -}}
