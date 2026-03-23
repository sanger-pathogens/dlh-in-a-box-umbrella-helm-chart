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
