{{/*
This chart's own name for app.kubernetes.io/name. Fixed rather than derived
from global.nameOverride -- that override was never meant to rename
individual dependency charts.
*/}}
{{- define "cloudbeaver.name" -}}
cloudbeaver
{{- end -}}

{{/* Shared labels, mirroring the umbrella chart's own dlh-in-a-box.labels shape. */}}
{{- define "cloudbeaver.labels" -}}
app.kubernetes.io/name: {{ include "cloudbeaver.name" . }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Service/resource name. Only touches .Release.Name, so it's safe to call from
any render context -- including the umbrella chart's own values.yaml, which
references it (via the shared Helm template namespace) to build the
cloudbeaver-auth-proxy oauth2-proxy upstream URL.
*/}}
{{- define "cloudbeaver.serviceName" -}}
{{- printf "%s-cloudbeaver" .Release.Name -}}
{{- end -}}
