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

{{- define "dlh-in-a-box.identity.apiBaseUrl" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $client := dig "external" "clients" "superset" dict $identity -}}
{{- if $client.apiBaseUrl -}}
{{- $client.apiBaseUrl -}}
{{- else -}}
{{- printf "%s/protocol/openid-connect" (include "dlh-in-a-box.identity.issuer" .) -}}
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

{{- define "dlh-in-a-box.identity.userInfoUrl" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $client := dig "external" "clients" "superset" dict $identity -}}
{{- if $client.userInfoUrl -}}
{{- $client.userInfoUrl -}}
{{- else -}}
{{- printf "%s/protocol/openid-connect/userinfo" (include "dlh-in-a-box.identity.issuer" .) -}}
{{- end -}}
{{- end -}}

{{- define "dlh-in-a-box.openldap.serviceName" -}}
{{- printf "%s-openldap" .Release.Name -}}
{{- end -}}

{{- define "dlh-in-a-box.platformHome.serviceName" -}}
{{- printf "%s-platform-home" .Release.Name -}}
{{- end -}}

{{- define "dlh-in-a-box.cloudbeaver.serviceName" -}}
{{- printf "%s-cloudbeaver" .Release.Name -}}
{{- end -}}

{{- define "dlh-in-a-box.group.app" -}}
{{- $root := .root -}}
{{- $name := .name -}}
{{- $identity := $root.Values.global.identity | default dict -}}
{{- $conventions := get $identity "groupConventions" | default dict -}}
{{- printf "%s%s" (default "dlh-app-" $conventions.appAccessPrefix) $name -}}
{{- end -}}

{{- define "dlh-in-a-box.group.role" -}}
{{- $root := .root -}}
{{- $name := .name -}}
{{- $identity := $root.Values.global.identity | default dict -}}
{{- $conventions := get $identity "groupConventions" | default dict -}}
{{- printf "%s%s" (default "dlh-role-" $conventions.rolePrefix) $name -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.directory.baseDn" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $directory := get $identity "directory" | default dict -}}
{{- $ldap := get $directory "ldap" | default dict -}}
{{- $openldap := .Values.openldap | default dict -}}
{{- $seed := get $openldap "seed" | default dict -}}
{{- if $seed.baseDn -}}
{{- $seed.baseDn -}}
{{- else if $ldap.userBaseDn -}}
{{- regexReplaceAll "^ou=[^,]+," $ldap.userBaseDn "" -}}
{{- else -}}
{{- printf "dc=%s" (replace "." ",dc=" (default "example.org" $seed.domain)) -}}
{{- end -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.directory.url" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $directory := get $identity "directory" | default dict -}}
{{- $ldap := get $directory "ldap" | default dict -}}
{{- $openldap := .Values.openldap | default dict -}}
{{- $service := get $openldap "service" | default dict -}}
{{- if $ldap.url -}}
{{- $ldap.url -}}
{{- else -}}
{{- printf "ldap://%s.%s.svc.cluster.local:%v" (include "dlh-in-a-box.openldap.serviceName" .) .Release.Namespace (default 389 $service.port) -}}
{{- end -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.directory.userBaseDn" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $directory := get $identity "directory" | default dict -}}
{{- $ldap := get $directory "ldap" | default dict -}}
{{- if $ldap.userBaseDn -}}
{{- $ldap.userBaseDn -}}
{{- else -}}
{{- printf "ou=people,%s" (include "dlh-in-a-box.identity.directory.baseDn" .) -}}
{{- end -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.directory.groupBaseDn" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $directory := get $identity "directory" | default dict -}}
{{- $ldap := get $directory "ldap" | default dict -}}
{{- if $ldap.groupBaseDn -}}
{{- $ldap.groupBaseDn -}}
{{- else -}}
{{- printf "ou=groups,%s" (include "dlh-in-a-box.identity.directory.baseDn" .) -}}
{{- end -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.directory.bindDn" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $directory := get $identity "directory" | default dict -}}
{{- $ldap := get $directory "ldap" | default dict -}}
{{- if $ldap.bindDistinguishedName -}}
{{- $ldap.bindDistinguishedName -}}
{{- else -}}
{{- printf "cn=admin,%s" (include "dlh-in-a-box.identity.directory.baseDn" .) -}}
{{- end -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.directory.bindSecretName" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $directory := get $identity "directory" | default dict -}}
{{- $ldap := get $directory "ldap" | default dict -}}
{{- if $ldap.bindExistingSecret -}}
{{- $ldap.bindExistingSecret -}}
{{- else -}}
{{- default "dlh-openldap-admin" (dig "auth" "existingSecret" "dlh-openldap-admin" .Values.openldap) -}}
{{- end -}}
{{- end -}}

{{- define "dlh-in-a-box.identity.directory.bindSecretKey" -}}
{{- $identity := .Values.global.identity | default dict -}}
{{- $directory := get $identity "directory" | default dict -}}
{{- $ldap := get $directory "ldap" | default dict -}}
{{- if $ldap.bindPasswordKey -}}
{{- $ldap.bindPasswordKey -}}
{{- else -}}
{{- default "adminPassword" (dig "auth" "adminPasswordKey" "adminPassword" .Values.openldap) -}}
{{- end -}}
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

{{- define "dlh-in-a-box.ranger.admin.url" -}}
{{- printf "http://%s.%s.svc.cluster.local:6080" (include "dlh-in-a-box.ranger.admin.serviceName" .) .Release.Namespace -}}
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
