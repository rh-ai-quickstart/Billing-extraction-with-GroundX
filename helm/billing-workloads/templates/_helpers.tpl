{{- define "billing-workloads.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "billing-workloads.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "billing-workloads.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "billing-workloads.labels" -}}
helm.sh/chart: {{ include "billing-workloads.chart" . }}
{{ include "billing-workloads.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "billing-workloads.selectorLabels" -}}
app.kubernetes.io/name: {{ include "billing-workloads.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "billing-workloads.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "billing-workloads.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
GroundX Python client base URL for the workbench notebook.

When notebook.groundx.baseUrl is unset/empty, derive the in-cluster URL from the
same naming rules as the groundx subchart (groundx.groundx.serviceUrl):
  http://<groundx.groundx.serviceName>.<namespace>.svc.cluster.local/api

Namespace: groundx.namespace, else Helm release namespace, else "eyelevel".
*/}}
{{- define "billing-workloads.groundxBaseUrlForNotebook" -}}
{{- $manual := .Values.notebook.groundx.baseUrl | default "" | trim -}}
{{- if $manual -}}
{{- $manual -}}
{{- else -}}
{{- $gxc := .Values.groundx.groundx | default dict -}}
{{- $svc := dig "serviceName" "groundx" $gxc -}}
{{- $ns := coalesce .Values.groundx.namespace .Release.Namespace "eyelevel" | trim -}}
{{- printf "http://%s.%s.svc.cluster.local/api" $svc $ns -}}
{{- end -}}
{{- end }}
