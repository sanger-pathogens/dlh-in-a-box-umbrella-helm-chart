{{/*
Renders one complete metastore instance: Service, Deployment (+ optional
Ingress), its metastore-site.xml config Secret, and its schema-init Job.

Call with (dict "context" $ "name" "<optional>"):
  - context: the root template context scoped to this chart's own Values
    (either this chart's own "$" when called from its own templates, or
    another chart's ".Subcharts.hive" when called from a parent composing
    multiple instances).
  - name: optional identity for this instance. Given, it becomes the
    Postgres database name and is woven into every resource name exactly as
    today's per-catalog resources were (so a parent calling this once per
    catalog name reproduces existing resource names unchanged). Omitted, it
    renders a single, plainly-named metastore backed by .Values.database --
    this chart's own default, self-sufficient behavior.

This chart has no notion of "catalogs" -- that's a concept owned by whoever
composes multiple named instances of it, not by the instance itself.
*/}}
{{- define "hive.metastoreInstance" -}}
{{- $ctx := .context -}}
{{- $name := .name | default "" -}}
{{- $database := $name | default $ctx.Values.database -}}
{{- $suffix := "" -}}
{{- $safeName := "" -}}
{{- if $name -}}
{{- $safeName = include "hive.sanitize" $name -}}
{{- $suffix = printf "-%s" $safeName -}}
{{- end -}}
{{- $postgresHost := include "hive.postgresHost" $ctx -}}
{{- $postgresPort := include "hive.postgresPort" $ctx -}}

---
apiVersion: v1
kind: Service
metadata:
  name: {{ include "hive.fullname" $ctx }}{{ $suffix }}-metastore
  namespace: {{ $ctx.Release.Namespace }}
spec:
  ports:
    - port: 9083
      targetPort: 9083
  selector:
    app: {{ include "hive.fullname" $ctx }}{{ $suffix }}-metastore

---
apiVersion: v1
kind: Secret
metadata:
  name: {{ include "hive.fullname" $ctx }}-metastore-cfg{{ $suffix }}
  namespace: {{ $ctx.Release.Namespace }}
  labels:
    app: {{ include "hive.fullname" $ctx }}-metastore
    metastore: {{ $database }}
type: Opaque
stringData:
  core-site.xml: |
    <configuration>
      <property>
        <name>fs.s3a.connection.ssl.enabled</name>
        <value>{{ hasPrefix "https://" $ctx.Values.s3.endpoint }}</value>
      </property>
      <property>
        <name>fs.s3a.endpoint</name>
        <value>{{ include "hive.xmlEscape" $ctx.Values.s3.endpoint }}</value>
      </property>
      <property>
        <name>fs.s3a.fast.upload</name>
        <value>true</value>
      </property>
      <property>
        <name>fs.s3a.access.key</name>
        <value>{{ include "hive.xmlEscape" (include "hive.s3AccessKey" $ctx) }}</value>
      </property>
      <property>
        <name>fs.s3a.secret.key</name>
        <value>{{ include "hive.xmlEscape" (include "hive.s3SecretKey" $ctx) }}</value>
      </property>
      <property>
        <name>fs.s3a.path.style.access</name>
        <value>{{ $ctx.Values.s3.pathStyleAccess }}</value>
      </property>
    </configuration>

  metastore-site.xml: |
    <configuration>
      <property>
        <name>metastore.task.threads.always</name>
        <value>org.apache.hadoop.hive.metastore.events.EventCleanerTask</value>
      </property>
      <property>
        <name>metastore.expression.proxy</name>
        <value>org.apache.hadoop.hive.metastore.DefaultPartitionExpressionProxy</value>
      </property>
      <property>
        <name>javax.jdo.option.ConnectionDriverName</name>
        <value>org.postgresql.Driver</value>
      </property>
      <property>
        <name>javax.jdo.option.ConnectionURL</name>
        <value>{{ include "hive.xmlEscape" (printf "jdbc:postgresql://%s:%s/%s" $postgresHost $postgresPort $database) }}</value>
      </property>
      <property>
        <name>javax.jdo.option.ConnectionUserName</name>
        <value>{{ include "hive.xmlEscape" (include "hive.postgresUsername" $ctx) }}</value>
      </property>
      <property>
        <name>javax.jdo.option.ConnectionPassword</name>
        <value>{{ include "hive.xmlEscape" (include "hive.postgresPassword" $ctx) }}</value>
      </property>
      <property>
        <name>datanucleus.connectionPoolingType</name>
        <value>DBCP</value>
      </property>
      <property>
        <name>datanucleus.connectionPool.maxActive</name>
        <value>20</value>
      </property>
      <property>
        <name>datanucleus.connectionPool.minIdle</name>
        <value>0</value>
      </property>
      <property>
        <name>datanucleus.connectionPool.maxIdle</name>
        <value>1</value>
      </property>
      <property>
        <name>metastore.warehouse.dir</name>
        <value>{{ include "hive.xmlEscape" (printf "%s/%s" $ctx.Values.warehouseDir $database) }}</value>
      </property>
      <property>
        <name>metastore.thrift.port</name>
        <value>9083</value>
      </property>
      <property>
        <name>hive.metastore.server.max.threads</name>
        <value>60</value>
      </property>
      <property>
        <name>hive.metastore.server.min.threads</name>
        <value>20</value>
      </property>
      <property>
        <name>hive.views-execution.enabled</name>
        <value>true</value>
      </property>
    </configuration>

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "hive.fullname" $ctx }}{{ $suffix }}-metastore
  namespace: {{ $ctx.Release.Namespace }}
spec:
  selector:
    matchLabels:
      app: {{ include "hive.fullname" $ctx }}{{ $suffix }}-metastore
  strategy:
    type: Recreate
  template:
    metadata:
      annotations:
        checksum/init-config: {{ printf "%s|%s" $postgresHost $postgresPort | sha256sum }}
        checksum/metastore-config: {{ printf "%s|%s|%s|%s" $postgresHost $postgresPort $database $ctx.Values.warehouseDir | sha256sum }}
        checksum/postgres-secret: {{ include "hive.postgresSecretChecksum" $ctx }}
        checksum/s3-secret: {{ include "hive.s3SecretChecksum" $ctx }}
      labels:
        app: {{ include "hive.fullname" $ctx }}{{ $suffix }}-metastore
    spec:
      initContainers:
        {{- include "hive.waitForPostgresInitContainer" $ctx | nindent 8 }}
        {{- include "hive.downloadJdbcInitContainer" $ctx | nindent 8 }}
        - name: wait-for-schema{{ $suffix }}
          image: "{{ $ctx.Values.schemainit.image.registry }}/{{ $ctx.Values.schemainit.image.repository }}:{{ $ctx.Values.schemainit.image.tag }}"
          command: ["/bin/sh", "-c"]
          args:
            - |
              JDBC_URL="jdbc:postgresql://$POSTGRES_HOST:$POSTGRES_PORT/{{ $database }}"
              until /opt/hive/bin/schematool \
                  -dbType postgres \
                  -driver org.postgresql.Driver \
                  -userName "$POSTGRES_USER" \
                  -passWord "$POSTGRES_PASSWORD" \
                  -url "$JDBC_URL" \
                  -info; do
                echo "Waiting for Hive schema '{{ $database }}' to become ready..."
                sleep 5
              done
              echo "Schema '{{ $database }}' is ready."
          env:
            - name: HADOOP_CLASSPATH
              value: /extra-jars/*
            {{- include "hive.postgresUserEnvEntry" $ctx | nindent 12 }}
            {{- include "hive.postgresPasswordEnvEntry" $ctx | nindent 12 }}
            - name: POSTGRES_HOST
              valueFrom:
                configMapKeyRef:
                  name: {{ include "hive.fullname" $ctx }}-init-config
                  key: POSTGRES_HOST
            - name: POSTGRES_PORT
              valueFrom:
                configMapKeyRef:
                  name: {{ include "hive.fullname" $ctx }}-init-config
                  key: POSTGRES_PORT
          volumeMounts:
            {{- include "hive.jdbcDriverVolumeMount" $ctx | nindent 12 }}
      containers:
        - name: metastore
          image: "{{ $ctx.Values.metastore.image.registry }}/{{ $ctx.Values.metastore.image.repository }}:{{ $ctx.Values.metastore.image.tag }}"
          imagePullPolicy: IfNotPresent
          env:
            - name: schema_name
              value: "{{ $database }}"
            - name: SERVICE_NAME
              value: metastore
            - name: DB_DRIVER
              value: postgres
            - name: IS_RESUME
              value: "true"
            - name: METASTORE_PORT
              value: "9083"
            - name: HIVE_CUSTOM_CONF_DIR
              value: /hive_custom_conf
            - name: HADOOP_OPTIONAL_TOOLS
              value: hadoop-aws
            - name: HADOOP_CLASSPATH
              value: /opt/hadoop/share/hadoop/tools/lib/*:/extra-jars/*
            - name: username
              {{- if $ctx.Values.postgresql.enabled }}
              value: "postgres"
              {{- else if $ctx.Values.externalDatabase.existingSecret }}
              valueFrom:
                secretKeyRef:
                  name: {{ $ctx.Values.externalDatabase.existingSecret }}
                  key: username
              {{- else }}
              value: {{ $ctx.Values.externalDatabase.user | quote }}
              {{- end }}
            - name: password
              valueFrom:
                secretKeyRef:
                  name: {{ include "hive.postgresSecretName" $ctx }}
                  key: {{ include "hive.postgresSecretKey" $ctx }}
          envFrom:
            - secretRef:
                name: {{ include "hive.s3SecretName" $ctx }}
            - configMapRef:
                name: {{ include "hive.fullname" $ctx }}-init-config
          ports:
            - containerPort: 9083
          volumeMounts:
            - name: metastore-cfg-vol
              mountPath: /hive_custom_conf
            {{- include "hive.jdbcDriverVolumeMount" $ctx | nindent 12 }}
      volumes:
        - name: metastore-cfg-vol
          secret:
            secretName: {{ include "hive.fullname" $ctx }}-metastore-cfg{{ $suffix }}
        {{- include "hive.jdbcDriverVolume" $ctx | nindent 8 }}

{{- if $ctx.Values.ingress.enabled }}
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "hive.fullname" $ctx }}{{ $suffix }}-metastore-ingress
  namespace: {{ $ctx.Release.Namespace }}
spec:
  {{- if $ctx.Values.ingress.className }}
  ingressClassName: {{ $ctx.Values.ingress.className }}
  {{- end }}
  rules:
    - host: {{ include "hive.fullname" $ctx }}{{ $suffix }}-metastore.{{ $ctx.Values.global.domain }}
      http:
        paths:
          - path: /
            pathType: ImplementationSpecific
            backend:
              service:
                name: {{ include "hive.fullname" $ctx }}{{ $suffix }}-metastore
                port:
                  number: 9083
  {{- if $ctx.Values.ingress.tlsSecretName }}
  tls:
    - secretName: {{ $ctx.Values.ingress.tlsSecretName }}
      hosts:
        - {{ include "hive.fullname" $ctx }}{{ $suffix }}-metastore.{{ $ctx.Values.global.domain }}
  {{- end }}
{{- end }}

{{- if $ctx.Values.schemainit.job.enabled }}
---
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ printf "%s-schema%s-%s" (include "hive.fullname" $ctx) $suffix ($ctx.Values.schemainit.image.tag | replace "." "-" | lower) | trunc 63 | trimSuffix "-" }}
  namespace: {{ $ctx.Release.Namespace }}
  labels:
    app: {{ include "hive.fullname" $ctx }}-schema-init
spec:
  backoffLimit: 1
  template:
    spec:
      restartPolicy: Never
      initContainers:
        {{- include "hive.waitForPostgresInitContainer" $ctx | nindent 8 }}
        {{- include "hive.downloadJdbcInitContainer" $ctx | nindent 8 }}
        {{- if $ctx.Values.postgresql.enabled }}
        - name: create-db{{ $suffix }}
          image: postgres:15
          command: ["/bin/sh", "-c"]
          args:
            - |
              set -e
              echo "Checking if database '{{ $database }}' exists..."
              if ! PGPASSWORD="$POSTGRES_PASSWORD" psql \
                  -h "$POSTGRES_HOST" \
                  -U "$POSTGRES_USER" \
                  -p "$POSTGRES_PORT" \
                  -d postgres \
                  -tAc "SELECT 1 FROM pg_database WHERE datname='{{ $database }}';" | grep -q 1; then
                echo "Creating database '{{ $database }}'..."
                PGPASSWORD="$POSTGRES_PASSWORD" psql \
                  -h "$POSTGRES_HOST" \
                  -U "$POSTGRES_USER" \
                  -p "$POSTGRES_PORT" \
                  -d postgres \
                  -c "CREATE DATABASE \"{{ $database }}\""
              else
                echo "Database '{{ $database }}' already exists."
              fi
          env:
            {{- include "hive.postgresUserEnvEntry" $ctx | nindent 12 }}
            {{- include "hive.postgresPasswordEnvEntry" $ctx | nindent 12 }}
            - name: POSTGRES_HOST
              valueFrom:
                configMapKeyRef:
                  name: {{ include "hive.fullname" $ctx }}-init-config
                  key: POSTGRES_HOST
            - name: POSTGRES_PORT
              valueFrom:
                configMapKeyRef:
                  name: {{ include "hive.fullname" $ctx }}-init-config
                  key: POSTGRES_PORT
        {{- end }}
      containers:
        - name: init-schema{{ $suffix }}
          image: "{{ $ctx.Values.schemainit.image.registry }}/{{ $ctx.Values.schemainit.image.repository }}:{{ $ctx.Values.schemainit.image.tag }}"
          command: ["/bin/sh", "-c"]
          args:
            - |
              set -e
              JDBC_URL="jdbc:postgresql://$POSTGRES_HOST:$POSTGRES_PORT/{{ $database }}"
              echo "Upgrading or verifying Hive schema for '{{ $database }}'..."
              if /opt/hive/bin/schematool \
                  -dbType postgres \
                  -driver org.postgresql.Driver \
                  -userName "$POSTGRES_USER" \
                  -passWord "$POSTGRES_PASSWORD" \
                  -url "$JDBC_URL" \
                  -upgradeSchema; then
                echo "Schema is current."
              else
                echo "No existing schema found, initializing..."
                /opt/hive/bin/schematool \
                  --verbose \
                  -dbType postgres \
                  -driver org.postgresql.Driver \
                  -userName "$POSTGRES_USER" \
                  -passWord "$POSTGRES_PASSWORD" \
                  -url "$JDBC_URL" \
                  -initSchema
              fi
          env:
            - name: HADOOP_CLASSPATH
              value: /extra-jars/*
            {{- include "hive.postgresUserEnvEntry" $ctx | nindent 12 }}
            {{- include "hive.postgresPasswordEnvEntry" $ctx | nindent 12 }}
            - name: POSTGRES_HOST
              valueFrom:
                configMapKeyRef:
                  name: {{ include "hive.fullname" $ctx }}-init-config
                  key: POSTGRES_HOST
            - name: POSTGRES_PORT
              valueFrom:
                configMapKeyRef:
                  name: {{ include "hive.fullname" $ctx }}-init-config
                  key: POSTGRES_PORT
          volumeMounts:
            {{- include "hive.jdbcDriverVolumeMount" $ctx | nindent 12 }}
      volumes:
        {{- include "hive.jdbcDriverVolume" $ctx | nindent 8 }}
{{- end }}
{{- end -}}
