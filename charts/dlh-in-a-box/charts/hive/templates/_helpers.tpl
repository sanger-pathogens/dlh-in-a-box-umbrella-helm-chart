{{/*
Sanitize schema name for Kubernetes resource names
*/}}
{{- define "hive.sanitize" -}}
{{- . | lower | replace "_" "-" | replace "." "-" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Escape text values embedded in Hadoop XML configuration files.
*/}}
{{- define "hive.xmlEscape" -}}
{{- replace ">" "&gt;" (replace "<" "&lt;" (replace "&" "&amp;" .)) -}}
{{- end -}}

{{/*
Full name for Hive resources
*/}}
{{- define "hive.fullname" -}}
{{- printf "%s-hive" .Release.Name -}}
{{- end -}}

{{/*
Fullname of the bundled PostgreSQL dependency (postgresql.enabled=true),
following the same nameOverride convention that dependency's own templates
use to name its Service/Secret -- not a guess, a read of the one field that
actually controls both.
*/}}
{{- define "hive.bundledPostgresFullname" -}}
{{- printf "%s-%s" .Release.Name (default "hive-postgresql" .Values.postgresql.nameOverride) -}}
{{- end -}}

{{/*
PostgreSQL service host: the bundled dependency's computed fullname when
postgresql.enabled=true, otherwise externalDatabase.host verbatim -- required
in that case, with no implicit fallback/guessing.
*/}}
{{- define "hive.postgresHost" -}}
{{- if .Values.postgresql.enabled -}}
{{- include "hive.bundledPostgresFullname" . -}}
{{- else -}}
{{- .Values.externalDatabase.host -}}
{{- end -}}
{{- end -}}

{{- define "hive.postgresPort" -}}
{{- if .Values.postgresql.enabled -}}
5432
{{- else -}}
{{- .Values.externalDatabase.port -}}
{{- end -}}
{{- end -}}

{{- define "hive.lookupSecretValue" -}}
{{- $secret := lookup "v1" "Secret" .namespace .secretName -}}
{{- if and $secret (hasKey $secret.data .secretKey) -}}
{{- index $secret.data .secretKey | b64dec -}}
{{- end -}}
{{- end -}}

{{- define "hive.postgresSecretName" -}}
{{- if .Values.postgresql.enabled -}}
{{- default (include "hive.bundledPostgresFullname" .) .Values.postgresql.auth.existingSecret -}}
{{- else -}}
{{- default (printf "%s-postgres-secret" (include "hive.fullname" .)) .Values.externalDatabase.existingSecret -}}
{{- end -}}
{{- end -}}

{{- define "hive.postgresSecretKey" -}}
{{- if .Values.postgresql.enabled -}}
postgres-password
{{- else -}}
password
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
{{- if .Values.postgresql.enabled -}}
postgres
{{- else -}}
{{- $resolved := "" -}}
{{- if .Values.externalDatabase.existingSecret -}}
  {{- $resolved = include "hive.lookupSecretValue" (dict "namespace" .Release.Namespace "secretName" .Values.externalDatabase.existingSecret "secretKey" "username") -}}
{{- end -}}
{{- default .Values.externalDatabase.user $resolved -}}
{{- end -}}
{{- end -}}

{{- define "hive.postgresPassword" -}}
{{- if .Values.postgresql.enabled -}}
{{- $resolved := "" -}}
{{- if .Values.postgresql.auth.existingSecret -}}
  {{- $resolved = include "hive.lookupSecretValue" (dict "namespace" .Release.Namespace "secretName" .Values.postgresql.auth.existingSecret "secretKey" "postgres-password") -}}
{{- end -}}
{{- default .Values.postgresql.auth.postgresPassword $resolved -}}
{{- else -}}
{{- $resolved := "" -}}
{{- if .Values.externalDatabase.existingSecret -}}
  {{- $resolved = include "hive.lookupSecretValue" (dict "namespace" .Release.Namespace "secretName" .Values.externalDatabase.existingSecret "secretKey" "password") -}}
{{- end -}}
{{- default .Values.externalDatabase.password $resolved -}}
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
{{- $ownExistingSecret := ternary .Values.postgresql.auth.existingSecret .Values.externalDatabase.existingSecret .Values.postgresql.enabled -}}
{{- if $ownExistingSecret -}}
{{- $secret := lookup "v1" "Secret" .Release.Namespace $ownExistingSecret -}}
{{- if $secret -}}
{{- $secret | toYaml | sha256sum -}}
{{- else -}}
external-secret-missing
{{- end -}}
{{- else if .Values.postgresql.enabled -}}
{{- .Values.postgresql.auth.postgresPassword | sha256sum -}}
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

{{/*
Env-var entries for the Postgres role Hive connects as. POSTGRES_USER is a
fixed literal ("postgres") for the bundled instance's superuser, or a
runtime secretKeyRef/literal for externalDatabase -- resolved by Kubernetes
at container start, not baked in at template time. POSTGRES_PASSWORD is
always a real secretKeyRef, since hive.postgresSecretName/postgresSecretKey
resolve to an actual Secret either way (the bundled dependency's own, or
externalDatabase's existingSecret / this chart's own generated fallback).
*/}}
{{- define "hive.postgresUserEnvEntry" -}}
- name: POSTGRES_USER
  {{- if .Values.postgresql.enabled }}
  value: "postgres"
  {{- else if .Values.externalDatabase.existingSecret }}
  valueFrom:
    secretKeyRef:
      name: {{ .Values.externalDatabase.existingSecret }}
      key: username
  {{- else }}
  value: {{ .Values.externalDatabase.user | quote }}
  {{- end }}
{{- end -}}

{{- define "hive.postgresPasswordEnvEntry" -}}
- name: POSTGRES_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "hive.postgresSecretName" . }}
      key: {{ include "hive.postgresSecretKey" . }}
{{- end -}}

{{- define "hive.waitForPostgresInitContainer" -}}
- name: wait-for-postgres
  image: postgres:15
  command: ["/bin/sh", "-c"]
  args:
    - |
      until pg_isready \
          -h "$POSTGRES_HOST" \
          -p "$POSTGRES_PORT" \
          -U "$POSTGRES_USER"; do
        echo "Waiting for PostgreSQL to become ready..."
        sleep 2
      done
  env:
    {{- include "hive.postgresUserEnvEntry" . | nindent 4 }}
    - name: POSTGRES_HOST
      value: {{ include "hive.postgresHost" . }}
    - name: POSTGRES_PORT
      value: {{ include "hive.postgresPort" . | quote }}
{{- end -}}

{{- define "hive.downloadJdbcInitContainer" -}}
- name: download-jdbc
  image: alpine:3
  command: ["/bin/sh", "-c"]
  args:
    - wget -qO /extra-jars/postgresql-jdbc.jar "{{ .Values.jdbcDriver.url }}"
  volumeMounts:
    - name: jdbc-driver
      mountPath: /extra-jars
{{- end -}}

{{- define "hive.jdbcDriverVolume" -}}
- name: jdbc-driver
  emptyDir: {}
{{- end -}}

{{- define "hive.jdbcDriverVolumeMount" -}}
- name: jdbc-driver
  mountPath: /extra-jars
{{- end -}}
