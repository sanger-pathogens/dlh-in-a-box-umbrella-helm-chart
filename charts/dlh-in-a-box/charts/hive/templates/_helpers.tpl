{{/*
Sanitize schema name for Kubernetes resource names
*/}}
{{- define "hive.sanitize" -}}
{{- . | lower | replace "_" "-" | replace "." "-" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Full name for Hive resources
*/}}
{{- define "hive.fullname" -}}
{{- printf "%s-hive" .Release.Name -}}
{{- end -}}

{{/*
Default PostgreSQL service host for the bundled Hive metadata database.
Allows the chart to remain release-name-safe while still permitting an
explicit external host override.
*/}}
{{- define "hive.postgresHost" -}}
{{- default (printf "%s-hive-postgresql" .Release.Name) .Values.postgres.host -}}
{{- end -}}

{{- define "hive.lookupSecretValue" -}}
{{- $secret := lookup "v1" "Secret" .namespace .secretName -}}
{{- if and $secret (hasKey $secret.data .secretKey) -}}
{{- index $secret.data .secretKey | b64dec -}}
{{- end -}}
{{- end -}}

{{- define "hive.postgresSecretName" -}}
{{- if .Values.postgres.existingSecret -}}
{{- .Values.postgres.existingSecret -}}
{{- else -}}
{{- printf "%s-postgres-secret" (include "hive.fullname" .) -}}
{{- end -}}
{{- end -}}

{{- define "hive.s3SecretName" -}}
{{- if .Values.s3.existingSecret -}}
{{- .Values.s3.existingSecret -}}
{{- else -}}
{{- printf "%s-s3-secret" (include "hive.fullname" .) -}}
{{- end -}}
{{- end -}}

{{- define "hive.postgresUsername" -}}
{{- $resolved := "" -}}
{{- if .Values.postgres.existingSecret -}}
  {{- $resolved = include "hive.lookupSecretValue" (dict "namespace" .Release.Namespace "secretName" (include "hive.postgresSecretName" .) "secretKey" "username") -}}
{{- end -}}
{{- if $resolved -}}
{{- $resolved -}}
{{- else -}}
{{- .Values.postgres.username -}}
{{- end -}}
{{- end -}}

{{- define "hive.postgresPassword" -}}
{{- $resolved := "" -}}
{{- if .Values.postgres.existingSecret -}}
  {{- $resolved = include "hive.lookupSecretValue" (dict "namespace" .Release.Namespace "secretName" (include "hive.postgresSecretName" .) "secretKey" "password") -}}
{{- end -}}
{{- if $resolved -}}
{{- $resolved -}}
{{- else -}}
{{- .Values.postgres.password -}}
{{- end -}}
{{- end -}}

{{- define "hive.s3AccessKey" -}}
{{- $resolved := "" -}}
{{- if .Values.s3.existingSecret -}}
  {{- $resolved = include "hive.lookupSecretValue" (dict "namespace" .Release.Namespace "secretName" (include "hive.s3SecretName" .) "secretKey" "accessKey") -}}
{{- end -}}
{{- if $resolved -}}
{{- $resolved -}}
{{- else -}}
{{- .Values.s3.accessKey -}}
{{- end -}}
{{- end -}}

{{- define "hive.s3SecretKey" -}}
{{- $resolved := "" -}}
{{- if .Values.s3.existingSecret -}}
  {{- $resolved = include "hive.lookupSecretValue" (dict "namespace" .Release.Namespace "secretName" (include "hive.s3SecretName" .) "secretKey" "secretKey") -}}
{{- end -}}
{{- if $resolved -}}
{{- $resolved -}}
{{- else -}}
{{- .Values.s3.secretKey -}}
{{- end -}}
{{- end -}}

{{- define "hive.postgresSecretChecksum" -}}
{{- if .Values.postgres.existingSecret -}}
{{- $secret := lookup "v1" "Secret" .Release.Namespace (include "hive.postgresSecretName" .) -}}
{{- if $secret -}}
{{- $secret | toYaml | sha256sum -}}
{{- else -}}
external-secret-missing
{{- end -}}
{{- else -}}
{{- include (print .Template.BasePath "/postgres-secret.yaml") . | sha256sum -}}
{{- end -}}
{{- end -}}

{{- define "hive.s3SecretChecksum" -}}
{{- if .Values.s3.existingSecret -}}
{{- $secret := lookup "v1" "Secret" .Release.Namespace (include "hive.s3SecretName" .) -}}
{{- if $secret -}}
{{- $secret | toYaml | sha256sum -}}
{{- else -}}
external-secret-missing
{{- end -}}
{{- else -}}
{{- include (print .Template.BasePath "/s3-secret.yaml") . | sha256sum -}}
{{- end -}}
{{- end -}}
