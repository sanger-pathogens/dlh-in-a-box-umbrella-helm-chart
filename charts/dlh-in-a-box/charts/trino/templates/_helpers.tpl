{{/*
Modified for dlh-in-a-box from the upstream Trino chart.
Local changes add catalog generation and access-control helpers for
umbrella-chart-driven data catalog composition, including group-based ACLs.
*/}}
{{/* vim: set filetype=mustache: */}}
{{/*
Expand the name of the chart.
*/}}
{{- define "trino.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "trino.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if hasPrefix .Release.Name $name }}
{{- $name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "trino.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "trino.coordinator" -}}
{{- if .Values.coordinatorNameOverride }}
{{- .Values.coordinatorNameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if hasPrefix .Release.Name $name }}
{{- printf "%s-%s" $name "coordinator" | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s-%s" .Release.Name $name "coordinator" | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "trino.worker" -}}
{{- if .Values.workerNameOverride }}
{{- .Values.workerNameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if hasPrefix .Release.Name $name }}
{{- printf "%s-%s" $name "worker" | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s-%s" .Release.Name $name "worker" | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}


{{- define "trino.catalog" -}}
{{ template "trino.fullname" . }}-catalog
{{- end -}}

{{/*
Sanitize catalog names for service/resource references without depending on other subcharts.
*/}}
{{- define "trino.sanitizeCatalogName" -}}
{{- . | lower | replace "_" "-" | replace "." "-" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "trino.labels" -}}
helm.sh/chart: {{ include "trino.chart" . }}
{{ include "trino.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- if .Values.commonLabels }}
{{ tpl (toYaml .Values.commonLabels) . }}
{{- end }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "trino.selectorLabels" -}}
app.kubernetes.io/name: {{ include "trino.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "trino.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "trino.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Return the proper image name
{{ include "trino.image" . }}

Code is inspired from bitnami/common

*/}}
{{- define "trino.image" -}}
{{- $repositoryName := .Values.image.repository -}}
{{- if .Values.image.useRepositoryAsSoleImageReference -}}
  {{- printf "%s" $repositoryName -}}
{{- else -}}
  {{- $repositoryName := .Values.image.repository -}}
  {{- $registryName := .Values.image.registry -}}
  {{- $separator := ":" -}}
  {{- $termination := (default .Chart.AppVersion .Values.image.tag) | toString -}}
  {{- if .Values.image.digest }}
    {{- $separator = "@" -}}
    {{- $termination = .Values.image.digest | toString -}}
  {{- end -}}
  {{- if $registryName }}
    {{- printf "%s/%s%s%s" $registryName $repositoryName $separator $termination -}}
  {{- else -}}
    {{- printf "%s%s%s"  $repositoryName $separator $termination -}}
  {{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create the secret name for the file-based authentication's password file
*/}}
{{- define "trino.passwordSecretName" -}}
{{- if and .Values.auth .Values.auth.passwordAuthSecret }}
{{- .Values.auth.passwordAuthSecret | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if hasPrefix .Release.Name $name }}
{{- printf "%s-%s" $name "password-file" | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s-%s" .Release.Name $name "password-file" | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create the secret name for the group-provider file
*/}}
{{- define "trino.groupsSecretName" -}}
{{- if and .Values.auth .Values.auth.groupAuthSecret }}
{{- .Values.auth.groupAuthSecret | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if hasPrefix .Release.Name $name }}
{{- printf "%s-%s" $name "groups-file" | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s-%s" .Release.Name $name "groups-file" | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "trino.dataCatalogs" -}}
{{- $global := get .Values "global" | default (dict) -}}
{{- toYaml (get $global "dataCatalogs" | default (dict)) -}}
{{- end -}}

{{- define "trino.catalogProperties" -}}
{{- $root := .root -}}
{{- $catalogName := .catalogName -}}
{{- $catalog := .catalog -}}
{{- $type := default "deltaLake" $catalog.type -}}
{{- $safeCatalog := include "trino.sanitizeCatalogName" $catalogName -}}
{{- $s3 := .s3 | default (dict) -}}
{{- $hiveFullname := printf "%s-hive" $root.Release.Name -}}
{{- if eq $type "deltaLake" }}
connector.name=delta_lake
hive.metastore.uri=thrift://{{ $hiveFullname }}-{{ $safeCatalog }}-metastore:9083
fs.native-s3.enabled=true
s3.aws-access-key={{ $s3.accessKey }}
s3.aws-secret-key={{ $s3.secretKey }}
s3.endpoint={{ $s3.endpoint }}
s3.region={{ $s3.region }}
s3.path-style-access={{ $s3.pathStyleAccess }}
delta.enable-non-concurrent-writes=true
delta.register-table-procedure.enabled=true
delta.metadata.cache-ttl=30s
{{- else if eq $type "hive" }}
connector.name=hive
hive.metastore.uri=thrift://{{ $hiveFullname }}-{{ $safeCatalog }}-metastore:9083
fs.native-s3.enabled=true
s3.aws-access-key={{ $s3.accessKey }}
s3.aws-secret-key={{ $s3.secretKey }}
s3.endpoint={{ $s3.endpoint }}
s3.region={{ $s3.region }}
s3.path-style-access={{ $s3.pathStyleAccess }}
{{- else }}
# Unsupported catalog type, please use deltaLake or hive
{{- end }}
{{- end -}}

{{- define "trino.accessControlRules" -}}
{{- $catalogs := (include "trino.dataCatalogs" . | fromYaml) | default (dict) -}}
{
  "catalogs": [
{{- $first := true }}
{{- range $catalogName, $catalog := $catalogs }}
  {{- $authorizedGroups := get $catalog "authorizedGroups" | default (dict) }}
  {{- $authorizedUsers := get $catalog "authorizedUsers" | default (dict) }}
  {{- $groupWrite := get $authorizedGroups "write" | default (list) }}
  {{- $groupRead := get $authorizedGroups "read" | default (list) }}
  {{- $userWrite := get $authorizedUsers "write" | default (list) }}
  {{- $userRead := get $authorizedUsers "read" | default (list) }}
  {{- range $group := $groupWrite }}
    {{- if not $first }},{{ end }}
    {"group":"{{ $group }}","catalog":"{{ $catalogName }}","allow":"all"}
    {{- $first = false }}
  {{- end }}
  {{- range $group := $groupRead }}
    {{- if not (has $group $groupWrite) }}
      {{- if not $first }},{{ end }}
      {"group":"{{ $group }}","catalog":"{{ $catalogName }}","allow":"read-only"}
      {{- $first = false }}
    {{- end }}
  {{- end }}
  {{- range $user := $userWrite }}
    {{- if not $first }},{{ end }}
    {"user":"{{ $user }}","catalog":"{{ $catalogName }}","allow":"all"}
    {{- $first = false }}
  {{- end }}
  {{- range $user := $userRead }}
    {{- if not (has $user $userWrite) }}
      {{- if not $first }},{{ end }}
      {"user":"{{ $user }}","catalog":"{{ $catalogName }}","allow":"read-only"}
      {{- $first = false }}
    {{- end }}
  {{- end }}
{{- end }}
  ]
}
{{- end -}}
