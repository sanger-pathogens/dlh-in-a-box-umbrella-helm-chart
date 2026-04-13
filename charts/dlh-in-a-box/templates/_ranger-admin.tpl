{{- define "dlh-in-a-box.rangerAdmin.installProperties" -}}
PYTHON_COMMAND_INVOKER=python3
LOGFILE=/var/log/ranger/ranger-admin-setup.log
RANGER_ADMIN_LOG_DIR=/var/log/ranger
RANGER_ADMIN_LOGBACK_CONF_FILE=/opt/ranger/admin/ews/webapp/WEB-INF/classes/conf/logback.xml
RANGER_PID_DIR_PATH=/var/run/ranger
app_home=/opt/ranger/admin/ews/webapp
DB_FLAVOR=POSTGRES
SQL_CONNECTOR_JAR=/usr/share/java/postgresql.jar
db_root_user=postgres
db_root_password=${RANGER_DB_ADMIN_PASSWORD}
db_host=${RANGER_DB_HOST}:${RANGER_DB_PORT}
db_name=${RANGER_DB_NAME}
db_user=${RANGER_DB_USERNAME}
db_password=${RANGER_DB_PASSWORD}
audit_db_name=${RANGER_DB_NAME}
audit_db_user=${RANGER_DB_USERNAME}
audit_db_password=${RANGER_DB_PASSWORD}
mysql_core_file=db/mysql/optimized/current/ranger_core_db_mysql.sql
oracle_core_file=db/oracle/optimized/current/ranger_core_db_oracle.sql
postgres_core_file=db/postgres/optimized/current/ranger_core_db_postgres.sql
sqlserver_core_file=db/sqlserver/optimized/current/ranger_core_db_sqlserver.sql
sqlanywhere_core_file=db/sqlanywhere/optimized/current/ranger_core_db_sqlanywhere.sql
postgres_audit_file=db/postgres/xa_audit_db_postgres.sql
rangerAdmin_password=${RANGER_ADMIN_PASSWORD}
rangerTagsync_password=${RANGER_TAGSYNC_PASSWORD:-rangertagsync}
rangerUsersync_password=${RANGER_USERSYNC_PASSWORD:-rangerusersync}
keyadmin_password=keyadmin
JAVA_VERSION_REQUIRED=1.8
audit_store=db
policymgr_external_url=${RANGER_POLICYMGR_EXTERNAL_URL}
policymgr_http_enabled=true
policymgr_supportedcomponents=tag,trino
unix_user=ranger
unix_user_pwd=ranger
unix_group=ranger
authentication_method=NONE
remoteLoginEnabled=true
authServiceHostName=localhost
authServicePort=5151
token_valid=30
cookie_domain=
cookie_path=/
admin_principal=
admin_keytab=
lookup_principal=
lookup_keytab=
audit_jaas_client_loginModuleName=
audit_jaas_client_loginModuleControlFlag=
audit_jaas_client_option_useKeyTab=
audit_jaas_client_option_storeKey=
audit_jaas_client_option_useTicketCache=
audit_jaas_client_option_serviceName=
audit_jaas_client_option_keyTab=
audit_jaas_client_option_principal=
hadoop_conf=/etc/hadoop/conf
sso_enabled=false
sso_providerurl=
sso_publickey=
cred_keystore_filename=
{{- end -}}

{{- define "dlh-in-a-box.rangerAdmin.startScript" -}}
#!/bin/bash
set -euo pipefail

find_ranger_admin_pid() {
  ps -ef \
    | grep -v grep \
    | grep -E 'org\.apache\.ranger\.server\.tomcat\.EmbeddedServer|org\.apache\.catalina\.startup\.Bootstrap' \
    | awk '{print $2}' \
    | head -n1
}

dump_ranger_logs() {
  shopt -s nullglob
  for log_file in /var/log/ranger/*; do
    echo "==== ${log_file} ===="
    cat "${log_file}" || true
  done
}

python3 - <<'PY'
import os
import pathlib
import socket
import time
from string import Template

host = os.environ["RANGER_DB_HOST"]
port = int(os.environ["RANGER_DB_PORT"])
deadline = time.time() + 300

while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=5):
            break
    except OSError:
        time.sleep(5)
else:
    raise SystemExit(f"Timed out waiting for PostgreSQL at {host}:{port}")

template = pathlib.Path("/opt/ranger/bootstrap/install.properties.tmpl").read_text()
rendered = Template(template).safe_substitute(os.environ)
pathlib.Path("/opt/ranger/admin/install.properties").write_text(rendered)
PY

mkdir -p /var/log/ranger /var/run/ranger
export LOGFILE=/var/log/ranger/ranger-admin-setup.log

if [ ! -e /opt/ranger/.setupDone ]; then
  cd /opt/ranger/admin
  set +e
  setup_output="$(./setup.sh 2>&1)"
  setup_status=$?
  set -e
  printf '%s\n' "${setup_output}"
  if [ "${setup_status}" -ne 0 ]; then
    if printf '%s\n' "${setup_output}" | grep -q "Old Password and New Password argument are same"; then
      echo "Ranger Admin password is already initialized; continuing without rerunning password setup."
    elif grep -q "Old Password and New Password argument are same" "${LOGFILE}" 2>/dev/null; then
      echo "Ranger Admin password is already initialized; continuing without rerunning password setup."
    else
      dump_ranger_logs
      exit 1
    fi
  fi
  touch /opt/ranger/.setupDone
fi

cd /opt/ranger/admin && ./ews/ranger-admin-services.sh start
RANGER_ADMIN_PID=""
for _ in {1..24}; do
  RANGER_ADMIN_PID="$(find_ranger_admin_pid)"
  if [ -n "${RANGER_ADMIN_PID}" ]; then
    break
  fi
  sleep 5
done

if [ -z "${RANGER_ADMIN_PID}" ]; then
  echo "Ranger Admin process did not stay up" >&2
  dump_ranger_logs
  exit 1
fi

while kill -0 "${RANGER_ADMIN_PID}" >/dev/null 2>&1; do
  sleep 5
done

echo "Ranger Admin process exited unexpectedly" >&2
dump_ranger_logs
exit 1
{{- end -}}
