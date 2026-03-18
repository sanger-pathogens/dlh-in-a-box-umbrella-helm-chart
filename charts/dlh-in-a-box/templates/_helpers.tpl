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
