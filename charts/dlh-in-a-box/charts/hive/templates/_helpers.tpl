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