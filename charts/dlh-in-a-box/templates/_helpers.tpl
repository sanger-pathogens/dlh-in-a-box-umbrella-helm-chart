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
