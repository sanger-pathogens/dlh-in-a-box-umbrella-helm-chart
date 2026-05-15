import base64
import datetime
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ldap3 import SUBTREE, Connection, Server, Tls
from ldap3.core.exceptions import LDAPBindError
from ldap3.utils.conv import escape_filter_chars

CONFIG_PATH = "/opt/platform-home-api/admin-config.json"
PORT = int(os.environ.get("PORT", "18080"))
RANGER_URL = os.environ.get("RANGER_URL", "").rstrip("/")
RANGER_PASSWORD = os.environ.get("RANGER_ADMIN_PASSWORD", "")
USERINFO_URL = os.environ.get("IDENTITY_USERINFO_URL", "")
EXPECTED_ISSUER = os.environ.get("IDENTITY_EXPECTED_ISSUER", "")
ROLES_CLAIM = os.environ.get("OIDC_ROLES_CLAIM", "platform_roles")
ADMIN_ROLES = [
    item.strip()
    for item in os.environ.get("PLATFORM_ADMIN_ROLES", "platform-admin").split(",")
    if item.strip()
]
LDAP_BIND_PASSWORD = os.environ.get("LDAP_BIND_PASSWORD", "")
ACCESS_CONTROL_STATE_CONFIGMAP_NAME = os.environ.get("ACCESS_CONTROL_STATE_CONFIGMAP_NAME", "")
ACCESS_CONTROL_STATE_CONFIGMAP_KEY = os.environ.get("ACCESS_CONTROL_STATE_CONFIGMAP_KEY", "state.json")
POD_NAMESPACE = os.environ.get("POD_NAMESPACE", "")
KUBERNETES_SERVICE_HOST = os.environ.get("KUBERNETES_SERVICE_HOST", "")
KUBERNETES_SERVICE_PORT = os.environ.get("KUBERNETES_SERVICE_PORT", "443")
SERVICEACCOUNT_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
SERVICEACCOUNT_CA_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
CACHE_TTL_SECONDS = 60


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = int(status)
        self.message = str(message)


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


CONFIG = load_config()
ACCESS_CONTROL_ENABLED = bool(CONFIG.get("admin", {}).get("accessControlEnabled", True))
ACCESS_CONTROL_DISABLED_MESSAGE = str(
    CONFIG.get("admin", {}).get("accessControlNotice")
    or "Use Keycloak Admin and Ranger Admin for access management in this environment."
)
ROLE_CATALOG = {
    str(role.get("key", "")): role
    for role in CONFIG.get("roles", [])
    if str(role.get("key", "")).strip()
}
HEALTH_CACHE = {}
HEALTH_CACHE_TTL_SECONDS = max(
    15,
    int(CONFIG.get("health", {}).get("refreshIntervalSeconds") or CACHE_TTL_SECONDS),
)
HTTPS_CONTEXT = ssl._create_unverified_context()
DIRECTORY_STATUS_CACHE = {"expires_at": 0, "payload": {}}


class PreserveRedirectHandler(urllib.request.HTTPRedirectHandler):
    def http_error_301(self, req, fp, code, msg, headers):
        return fp

    http_error_302 = http_error_301
    http_error_303 = http_error_301
    http_error_307 = http_error_301
    http_error_308 = http_error_301


HEALTHCHECK_OPENER = urllib.request.build_opener(
    urllib.request.HTTPHandler(),
    urllib.request.HTTPSHandler(context=HTTPS_CONTEXT),
    PreserveRedirectHandler(),
)


def json_response(handler, status, payload):
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def utc_timestamp():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def normalize_iso8601(value):
    raw = str(value or "").strip()
    if not raw:
        raise ApiError(400, "expiresAt is required.")
    if len(raw) == 10:
        raw = f"{raw}T23:59:59Z"
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    elif "T" not in raw:
        raw = f"{raw}T23:59:59+00:00"
    try:
        parsed = datetime.datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ApiError(400, "expiresAt must be an ISO-8601 timestamp or a YYYY-MM-DD date.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed.astimezone(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def iso_to_epoch(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        parsed = datetime.datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return int(parsed.astimezone(datetime.timezone.utc).timestamp())


def read_json(handler):
    raw_length = handler.headers.get("Content-Length", "0")
    try:
        length = int(raw_length)
    except ValueError as exc:
        raise ApiError(400, "Invalid Content-Length header.") from exc
    if length <= 0:
        return {}
    payload = handler.rfile.read(length).decode("utf-8")
    if not payload.strip():
        return {}
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ApiError(400, "Request body must be valid JSON.") from exc


def bearer_token(handler):
    auth_header = str(handler.headers.get("Authorization", ""))
    if not auth_header.startswith("Bearer "):
        raise ApiError(401, "A bearer access token is required.")
    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise ApiError(401, "A bearer access token is required.")
    return token


def decode_token_claims(token):
    parts = token.split(".")
    if len(parts) < 2:
        return {}
    payload = parts[1]
    payload += "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload.encode("ascii")).decode("utf-8")
        claims = json.loads(decoded)
    except Exception:
        return {}
    return claims if isinstance(claims, dict) else {}


def userinfo(token):
    if not USERINFO_URL:
        raise ApiError(500, "The portal admin API is missing its identity userinfo endpoint.")
    request = urllib.request.Request(
        USERINFO_URL,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise ApiError(401, "Your session is no longer valid. Please sign in again.") from exc
        raise


def normalize_claim_values(value):
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def validate_token_claims(claims):
    if not isinstance(claims, dict) or not claims:
        raise ApiError(401, "Your session is no longer valid. Please sign in again.")

    now = int(time.time())
    exp = claims.get("exp")
    if not isinstance(exp, (int, float)) or int(exp) <= now:
        raise ApiError(401, "Your session is no longer valid. Please sign in again.")

    nbf = claims.get("nbf")
    if isinstance(nbf, (int, float)) and int(nbf) > now:
        raise ApiError(401, "Your session is not active yet. Please sign in again.")

    issuer = str(claims.get("iss", "")).strip()
    if EXPECTED_ISSUER and issuer and issuer != EXPECTED_ISSUER:
        raise ApiError(401, "Your session is no longer valid. Please sign in again.")


def authenticate(handler, require_admin=True):
    token = bearer_token(handler)
    claims = decode_token_claims(token)
    validate_token_claims(claims)
    profile = {}
    try:
        profile = userinfo(token)
    except ApiError as exc:
        if exc.status != 401:
            raise
    roles = normalize_claim_values(profile.get(ROLES_CLAIM))
    if not roles:
        roles = normalize_claim_values(claims.get(ROLES_CLAIM))
    is_admin = any(role in roles for role in ADMIN_ROLES)
    if require_admin and not is_admin:
        raise ApiError(403, "Platform administration is limited to platform administrators.")
    merged = dict(claims)
    merged.update(profile if isinstance(profile, dict) else {})
    merged["accessToken"] = token
    merged["roles"] = roles
    merged["is_admin"] = is_admin
    return merged


def launcher_catalog():
    launchers = CONFIG.get("launchers")
    return launchers if isinstance(launchers, dict) else {}


def launcher_entry(name):
    launcher = launcher_catalog().get(str(name))
    if not isinstance(launcher, dict):
        raise ApiError(404, "That portal launcher is not configured.")
    return launcher


def authorize_launcher(launcher, profile):
    required_roles = normalize_claim_values(launcher.get("requiredRoles"))
    roles = normalize_claim_values(profile.get("roles"))
    if required_roles and not any(role in roles for role in required_roles):
        raise ApiError(403, "You do not have access to that launcher.")


def launcher_request(url, payload=None, extra_headers=None):
    headers = {"Accept": "application/json"}
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if isinstance(extra_headers, dict):
        for key, value in extra_headers.items():
            if key and value is not None:
                headers[str(key)] = str(value)
    request = urllib.request.Request(url, headers=headers, data=body, method="POST" if payload is not None else "GET")
    try:
        if url.startswith("https://"):
            with urllib.request.urlopen(request, timeout=30, context=HTTPS_CONTEXT) as response:
                raw = response.read().decode("utf-8")
        else:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ApiError(502, f"Launcher upstream request failed with {exc.code}: {detail[:200]}") from exc
    except urllib.error.URLError as exc:
        raise ApiError(502, f"Launcher upstream request failed: {exc.reason}") from exc
    try:
        return json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        raise ApiError(502, "Launcher upstream returned invalid JSON.") from exc


def resolve_launcher(name, profile):
    launcher = launcher_entry(name)
    authorize_launcher(launcher, profile)
    mode = str(launcher.get("mode") or "redirect").strip().lower()

    if mode == "redirect":
        target_url = str(launcher.get("targetUrl") or "").strip()
        if not target_url:
            raise ApiError(500, "That portal launcher is missing its targetUrl.")
        return {"mode": "redirect", "url": target_url}

    if mode == "vault-oidc":
        internal_api_url = str(launcher.get("internalApiUrl") or "").rstrip("/")
        redirect_uri = str(launcher.get("redirectUri") or "").strip()
        complete_url = str(launcher.get("completeUrl") or "").strip()
        role = str(launcher.get("role") or "").strip()
        if not internal_api_url or not redirect_uri:
            raise ApiError(500, "The Vault launcher is missing its internal API URL or redirect URI.")
        payload = {"redirect_uri": redirect_uri}
        if role:
            payload["role"] = role
        response = launcher_request(f"{internal_api_url}/v1/auth/oidc/oidc/auth_url", payload)
        auth_url = str(((response.get("data") or {}).get("auth_url")) or "").strip()
        if not auth_url:
            raise ApiError(502, "Vault did not return an OIDC authorization URL.")
        return {
            "mode": "popup",
            "url": auth_url,
            "completeUrl": complete_url or redirect_uri.rsplit("/ui/vault/auth/oidc/oidc/callback", 1)[0] + "/ui/",
        }

    if mode == "vault-wrapped-token":
        internal_api_url = str(launcher.get("internalApiUrl") or "").rstrip("/")
        target_url = str(launcher.get("targetUrl") or "").strip()
        auth_mount = str(launcher.get("authMount") or "").strip()
        role = str(launcher.get("role") or "").strip()
        wrap_ttl = str(launcher.get("wrapTtl") or "").strip()
        access_token = str(profile.get("accessToken") or "").strip()
        if not internal_api_url or not target_url or not auth_mount or not role:
            raise ApiError(500, "The Vault launcher is missing its internal API URL, auth mount, role, or target URL.")
        if not access_token:
            raise ApiError(401, "Your session is no longer valid. Please sign in again.")
        request_headers = {}
        if wrap_ttl:
            request_headers["X-Vault-Wrap-TTL"] = wrap_ttl
        response = launcher_request(
            f"{internal_api_url}/v1/auth/{urllib.parse.quote(auth_mount, safe='')}/login",
            {"jwt": access_token, "role": role},
            request_headers,
        )
        wrap_token = str(((response.get("wrap_info") or {}).get("token")) or "").strip()
        if not wrap_token:
            raise ApiError(502, "Vault did not return a wrapped login token.")
        parsed_target = urllib.parse.urlparse(target_url)
        existing_query = urllib.parse.parse_qsl(parsed_target.query, keep_blank_values=True)
        existing_query.append(("wrapped_token", wrap_token))
        launched_url = urllib.parse.urlunparse(
            parsed_target._replace(query=urllib.parse.urlencode(existing_query))
        )
        return {"mode": "redirect", "url": launched_url}

    raise ApiError(500, f"Unsupported launcher mode: {mode}")


def ranger_enabled():
    return bool(CONFIG.get("ranger", {}).get("enabled")) and bool(RANGER_URL) and bool(RANGER_PASSWORD)


def ldap_config():
    ldap = CONFIG.get("ldap") if isinstance(CONFIG.get("ldap"), dict) else {}
    return ldap


def directory_enabled():
    ldap = ldap_config()
    return bool(
        ldap.get("enabled")
        and ldap.get("url")
        and ldap.get("userBaseDn")
        and ldap.get("groupBaseDn")
    )


def ranger_request(method, path, payload=None, ok=(200, 201), parse_json=True):
    if not ranger_enabled():
        raise ApiError(503, "Ranger administration is not enabled for this environment.")
    url = f"{RANGER_URL}{path}"
    headers = {
        "Authorization": "Basic "
        + base64.b64encode(f"admin:{RANGER_PASSWORD}".encode("utf-8")).decode("ascii"),
        "Accept": "application/json",
    }
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            if not parse_json:
                return raw
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        if exc.code in ok:
            raw = exc.read().decode("utf-8")
            if not parse_json:
                return raw
            return json.loads(raw) if raw else None
        if exc.code == 404:
            raise ApiError(404, "Requested Ranger resource was not found.") from exc
        raise


def role_update_path(role_id):
    return f"/service/public/v2/api/roles/{role_id}?createNonExistUserGroup=true"


def attr_value(entry, name):
    try:
        return str(entry[name].value or "").strip()
    except Exception:
        return ""


def build_display_name(username, first_name="", last_name=""):
    display_name = " ".join(part for part in [str(first_name or "").strip(), str(last_name or "").strip()] if part)
    return display_name or str(username or "").strip()


def ldap_connection():
    if not directory_enabled():
        raise ApiError(503, "LDAP-backed discovery is not configured for this environment.")
    ldap = ldap_config()
    parsed = urllib.parse.urlparse(str(ldap.get("url", "")).strip())
    use_ssl = parsed.scheme == "ldaps"
    host = parsed.hostname or str(ldap.get("url", "")).strip()
    port = parsed.port or (636 if use_ssl else 389)
    tls = None
    if use_ssl:
        trusted_ca_path = str(ldap.get("trustedCaPath", "") or "").strip()
        if ldap.get("allowInsecure", False):
            tls = Tls(validate=ssl.CERT_NONE)
        elif trusted_ca_path and os.path.exists(trusted_ca_path):
            tls = Tls(validate=ssl.CERT_REQUIRED, ca_certs_file=trusted_ca_path)
        else:
            tls = Tls(validate=ssl.CERT_REQUIRED)
    server = Server(host, port=port, use_ssl=use_ssl, tls=tls, get_info=None)
    bind_dn = str(ldap.get("bindDn") or "").strip()
    if bind_dn and LDAP_BIND_PASSWORD:
        try:
            return Connection(server, user=bind_dn, password=LDAP_BIND_PASSWORD, auto_bind=True)
        except LDAPBindError:
            print(f"LDAP bind failed for {bind_dn}; falling back to anonymous read", file=sys.stderr, flush=True)
    return Connection(server, auto_bind=True)


def directory_status(force_refresh=False):
    now = time.time()
    if not force_refresh and DIRECTORY_STATUS_CACHE["expires_at"] > now:
        return DIRECTORY_STATUS_CACHE["payload"]

    ldap = ldap_config()
    payload = {
        "enabled": bool(ldap.get("enabled")),
        "ldapReachable": False,
        "message": "",
    }
    if not directory_enabled():
        payload["message"] = "LDAP-backed directory discovery is not configured."
        DIRECTORY_STATUS_CACHE["payload"] = payload
        DIRECTORY_STATUS_CACHE["expires_at"] = now + CACHE_TTL_SECONDS
        return payload

    try:
        conn = ldap_connection()
        conn.unbind()
        payload["ldapReachable"] = True
        payload["message"] = "LDAP-backed discovery is available."
    except Exception as exc:
        payload["message"] = f"LDAP connectivity check failed: {exc}"

    DIRECTORY_STATUS_CACHE["payload"] = payload
    DIRECTORY_STATUS_CACHE["expires_at"] = now + CACHE_TTL_SECONDS
    return payload


def unique_non_empty(values):
    seen = set()
    ordered = []
    for value in values or []:
        candidate = str(value or "").strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        ordered.append(candidate)
    return ordered


def render_directory_filter(filter_template, replacement, fallback):
    template = str(filter_template or "").strip()
    if not template:
        return fallback
    if "{0}" in template:
        return template.replace("{0}", replacement)
    return template


def search_directory(kind, query, limit=20):
    status = directory_status()
    if not status.get("ldapReachable"):
        raise ApiError(503, status.get("message") or "LDAP-backed discovery is unavailable.")
    ldap = ldap_config()
    escaped = escape_filter_chars(str(query or "").strip())
    if not escaped:
        return []

    conn = ldap_connection()
    try:
        if kind == "group":
            group_name_attribute = str(ldap.get("groupNameAttribute") or "cn")
            group_filter = str(ldap.get("groupSearchFilter") or "(cn=*)")
            ldap_filter = f"(&{group_filter}({group_name_attribute}=*{escaped}*))"
            conn.search(
                ldap.get("groupBaseDn"),
                ldap_filter,
                search_scope=SUBTREE,
                attributes=[group_name_attribute],
                size_limit=limit,
            )
            results = []
            seen = set()
            for entry in conn.entries:
                name = attr_value(entry, group_name_attribute)
                if not name or name in seen:
                    continue
                seen.add(name)
                results.append({"name": name, "displayName": name, "email": ""})
            return sorted(results, key=lambda item: item["name"].casefold())

        username_attribute = str(ldap.get("usernameAttribute") or "uid")
        first_name_attribute = str(ldap.get("firstNameAttribute") or "givenName")
        last_name_attribute = str(ldap.get("lastNameAttribute") or "sn")
        email_attribute = str(ldap.get("emailAttribute") or "mail")
        user_filter = render_directory_filter(
            ldap.get("userSearchFilter"),
            "*",
            f"({username_attribute}=*)",
        )
        search_attributes = unique_non_empty(
            [username_attribute, first_name_attribute, last_name_attribute, email_attribute]
        )
        search_terms = "".join(f"({attribute}=*{escaped}*)" for attribute in search_attributes)
        ldap_filter = f"(&{user_filter}(|{search_terms}))"
        conn.search(
            ldap.get("userBaseDn"),
            ldap_filter,
            search_scope=SUBTREE,
            attributes=search_attributes,
            size_limit=limit,
        )
        results = []
        seen = set()
        for entry in conn.entries:
            username = attr_value(entry, username_attribute)
            if not username or username in seen:
                continue
            seen.add(username)
            first_name = attr_value(entry, first_name_attribute)
            last_name = attr_value(entry, last_name_attribute)
            email = attr_value(entry, email_attribute)
            results.append(
                {
                    "name": username,
                    "displayName": build_display_name(username, first_name, last_name),
                    "email": email,
                }
            )
        return sorted(results, key=lambda item: (item["displayName"] or item["name"]).casefold())
    finally:
        try:
            conn.unbind()
        except Exception:
            pass


def lookup_directory_principal(kind, name):
    status = directory_status()
    if not status.get("ldapReachable"):
        raise ApiError(503, status.get("message") or "LDAP-backed discovery is unavailable.")
    ldap = ldap_config()
    principal = str(name or "").strip()
    if not principal:
        return None
    conn = ldap_connection()
    try:
        if kind == "group":
            attribute = str(ldap.get("groupNameAttribute") or "cn")
            base_filter = str(ldap.get("groupSearchFilter") or "(cn=*)")
            ldap_filter = f"(&{base_filter}({attribute}={escape_filter_chars(principal)}))"
            conn.search(
                ldap.get("groupBaseDn"),
                ldap_filter,
                search_scope=SUBTREE,
                attributes=[attribute],
                size_limit=1,
            )
            if not conn.entries:
                return None
            return {"name": attr_value(conn.entries[0], attribute), "displayName": attr_value(conn.entries[0], attribute), "email": ""}

        username_attribute = str(ldap.get("usernameAttribute") or "uid")
        first_name_attribute = str(ldap.get("firstNameAttribute") or "givenName")
        last_name_attribute = str(ldap.get("lastNameAttribute") or "sn")
        email_attribute = str(ldap.get("emailAttribute") or "mail")
        base_filter = render_directory_filter(
            ldap.get("userSearchFilter"),
            escape_filter_chars(principal),
            f"({username_attribute}=*)",
        )
        ldap_filter = f"(&{base_filter}({username_attribute}={escape_filter_chars(principal)}))"
        conn.search(
            ldap.get("userBaseDn"),
            ldap_filter,
            search_scope=SUBTREE,
            attributes=unique_non_empty(
                [username_attribute, first_name_attribute, last_name_attribute, email_attribute]
            ),
            size_limit=1,
        )
        if not conn.entries:
            return None
        entry = conn.entries[0]
        username = attr_value(entry, username_attribute)
        return {
            "name": username,
            "displayName": build_display_name(
                username,
                attr_value(entry, first_name_attribute),
                attr_value(entry, last_name_attribute),
            ),
            "email": attr_value(entry, email_attribute),
        }
    finally:
        try:
            conn.unbind()
        except Exception:
            pass


def kubernetes_api_enabled():
    return bool(
        ACCESS_CONTROL_STATE_CONFIGMAP_NAME
        and POD_NAMESPACE
        and KUBERNETES_SERVICE_HOST
        and os.path.exists(SERVICEACCOUNT_TOKEN_PATH)
    )


def kubernetes_request(method, path, payload=None, ok=(200,), parse_json=True, content_type="application/json"):
    if not kubernetes_api_enabled():
        raise ApiError(503, "Access-control state storage is not configured for this environment.")
    with open(SERVICEACCOUNT_TOKEN_PATH, "r", encoding="utf-8") as handle:
        token = handle.read().strip()
    if not token:
        raise ApiError(503, "The platform-home admin API service account token is unavailable.")
    context = ssl.create_default_context(cafile=SERVICEACCOUNT_CA_PATH) if os.path.exists(SERVICEACCOUNT_CA_PATH) else ssl.create_default_context()
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = content_type
    request = urllib.request.Request(
        f"https://{KUBERNETES_SERVICE_HOST}:{KUBERNETES_SERVICE_PORT}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=30, context=context) as response:
        raw = response.read().decode("utf-8")
        if not parse_json:
            return raw
        return json.loads(raw) if raw else None


def default_state_document():
    return {"version": 1, "exceptions": []}


def load_state_document():
    if not kubernetes_api_enabled():
        return default_state_document()
    namespace = urllib.parse.quote(POD_NAMESPACE, safe="")
    configmap_name = urllib.parse.quote(ACCESS_CONTROL_STATE_CONFIGMAP_NAME, safe="")
    try:
        configmap = kubernetes_request(
            "GET",
            f"/api/v1/namespaces/{namespace}/configmaps/{configmap_name}",
            ok=(200,),
        )
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return default_state_document()
        raise ApiError(503, f"Unable to read the access-control state ConfigMap: {exc}") from exc
    raw_state = str((configmap.get("data") or {}).get(ACCESS_CONTROL_STATE_CONFIGMAP_KEY, "") or "").strip()
    if not raw_state:
        return default_state_document()
    try:
        document = json.loads(raw_state)
    except json.JSONDecodeError:
        return default_state_document()
    if not isinstance(document, dict):
        return default_state_document()
    exceptions = document.get("exceptions")
    if not isinstance(exceptions, list):
        document["exceptions"] = []
    document.setdefault("version", 1)
    return document


def save_state_document(document):
    if not kubernetes_api_enabled():
        raise ApiError(503, "Access-control state storage is unavailable in this environment.")
    serialized = json.dumps(document, sort_keys=True, indent=2)
    namespace = urllib.parse.quote(POD_NAMESPACE, safe="")
    configmap_name = urllib.parse.quote(ACCESS_CONTROL_STATE_CONFIGMAP_NAME, safe="")
    try:
        current = kubernetes_request(
            "GET",
            f"/api/v1/namespaces/{namespace}/configmaps/{configmap_name}",
            ok=(200,),
        )
        payload = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": ACCESS_CONTROL_STATE_CONFIGMAP_NAME,
                "namespace": POD_NAMESPACE,
                "resourceVersion": ((current.get("metadata") or {}).get("resourceVersion")),
            },
            "data": {
                ACCESS_CONTROL_STATE_CONFIGMAP_KEY: serialized,
            },
        }
        kubernetes_request(
            "PUT",
            f"/api/v1/namespaces/{namespace}/configmaps/{configmap_name}",
            payload=payload,
            ok=(200,),
        )
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise ApiError(503, f"Unable to update the access-control state ConfigMap: {exc}") from exc
        payload = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": ACCESS_CONTROL_STATE_CONFIGMAP_NAME,
                "namespace": POD_NAMESPACE,
            },
            "data": {
                ACCESS_CONTROL_STATE_CONFIGMAP_KEY: serialized,
            },
        }
        try:
            kubernetes_request(
                "POST",
                f"/api/v1/namespaces/{namespace}/configmaps",
                payload=payload,
                ok=(201,),
            )
        except urllib.error.HTTPError as inner_exc:
            raise ApiError(503, f"Unable to create the access-control state ConfigMap: {inner_exc}") from inner_exc


def exception_support_enabled():
    return kubernetes_api_enabled()


def ensure_access_control_enabled():
    if not ACCESS_CONTROL_ENABLED:
        raise ApiError(409, ACCESS_CONTROL_DISABLED_MESSAGE)


def active_exception(exception, now=None):
    if not isinstance(exception, dict):
        return False
    if str(exception.get("status", "active") or "active").lower() != "active":
        return False
    expires_at = iso_to_epoch(exception.get("expiresAt"))
    if expires_at is None:
        return False
    return expires_at > int(now or time.time())


def role_exceptions(document, role_key):
    now = int(time.time())
    active = []
    for exception in document.get("exceptions", []):
        if str(exception.get("platformRole", "")) != str(role_key):
            continue
        if active_exception(exception, now=now):
            active.append(exception)
    return sorted(active, key=lambda item: (str(item.get("displayName") or item.get("username") or "")).casefold())


def normalize_role_members(items):
    members = {}
    for item in items or []:
        if isinstance(item, dict):
            name = str(item.get("name", "")).strip()
            is_admin = bool(item.get("isAdmin", False))
        else:
            name = str(item).strip()
            is_admin = False
        if not name:
            continue
        current = members.get(name)
        members[name] = {"name": name, "isAdmin": is_admin or bool(current and current.get("isAdmin"))}
    return [members[name] for name in sorted(members)]


def extract_member_names(items):
    return [item["name"] for item in normalize_role_members(items)]


def list_roles():
    roles = []
    start_index = 0
    page_size = 200
    while True:
        page = ranger_request(
            "GET",
            f"/service/public/v2/api/roles?startIndex={start_index}&pageSize={page_size}",
            ok=(200,),
        ) or []
        if not isinstance(page, list):
            break
        roles.extend(page)
        if len(page) < page_size:
            break
        start_index += page_size
    return roles


def get_role_by_name(role_name):
    for role in list_roles():
        if str(role.get("name", "")) == str(role_name):
            return role
    return None


def role_view(role_entry, live_role, state_document):
    active_exceptions = role_exceptions(state_document, role_entry.get("key"))
    declared_users = extract_member_names(role_entry.get("users", []))
    live_users = extract_member_names(live_role.get("users", [])) if live_role else []
    live_groups = extract_member_names(live_role.get("groups", [])) if live_role else extract_member_names(role_entry.get("directoryGroups", []))
    return {
        "key": role_entry.get("key"),
        "name": role_entry.get("name") or role_entry.get("key"),
        "displayName": role_entry.get("displayName", ""),
        "manageable": bool(role_entry.get("manageable", True)),
        "description": role_entry.get("description", ""),
        "nestedRoles": role_entry.get("nestedRoles", []),
        "declaredExceptionsCount": len(role_entry.get("declaredExceptions", [])),
        "apps": role_entry.get("apps", {}),
        "policySummaries": role_entry.get("policySummaries", []),
        "members": {
            "users": sorted(set(live_users).union(declared_users)),
            "groups": live_groups,
        },
        "exceptions": {
            "declared": role_entry.get("declaredExceptions", []),
            "active": active_exceptions,
        },
    }


def role_entry_for_key(role_key):
    role_entry = ROLE_CATALOG.get(str(role_key))
    if not role_entry:
        raise ApiError(404, f"Platform role {role_key} is not defined in Git.")
    if role_entry.get("manageable", True) is False:
        raise ApiError(403, f"Platform role {role_key} is not manageable through the portal.")
    return role_entry


def list_platform_roles():
    state_document = load_state_document()
    live_roles = {}
    if ranger_enabled():
        live_roles = {
            str(role.get("name", "")): role
            for role in list_roles()
            if str(role.get("name", "")).strip()
        }
    views = []
    for role_key in sorted(ROLE_CATALOG):
        role_entry = ROLE_CATALOG[role_key]
        live_role = live_roles.get(role_entry.get("name") or role_key)
        views.append(role_view(role_entry, live_role, state_document))
    return views


def visible_items_for(profile):
    roles = set(normalize_claim_values(profile.get("roles")))
    is_admin = bool(profile.get("is_admin"))
    visible = []
    for item in CONFIG.get("items", []):
        if not isinstance(item, dict):
            continue
        if item.get("adminOnly") and not is_admin:
            continue
        required_roles = {
            str(role).strip()
            for role in (item.get("requiredRoles") or [])
            if str(role).strip()
        }
        if required_roles and roles.isdisjoint(required_roles):
            continue
        visible.append(item)
    return visible


def normalize_expected_status_codes(values):
    codes = []
    for value in values or []:
        try:
            codes.append(int(value))
        except (TypeError, ValueError):
            continue
    return codes or [200]


def health_payload(item, status, summary, checked_at=None):
    health = item.get("health") if isinstance(item, dict) else {}
    if not isinstance(health, dict):
        health = {}
    browser_target = str(item.get("url", "")).strip()
    probe_target = str(health.get("targetUrl", "")).strip()
    return {
        "id": str(item.get("id", "")).strip(),
        "label": str(item.get("name", "")).strip(),
        "group": str(item.get("group", "")).strip(),
        "status": status,
        "summary": summary,
        "checkedAt": checked_at or utc_timestamp(),
        "targetUrl": browser_target or probe_target,
        "probeTargetUrl": probe_target or browser_target,
    }


def probe_item_health(item):
    item_id = str(item.get("id", "")).strip()
    cache_entry = HEALTH_CACHE.get(item_id)
    now = time.time()
    if cache_entry and cache_entry.get("expires_at", 0) > now:
        return cache_entry["payload"]

    health = item.get("health") if isinstance(item, dict) else {}
    if not isinstance(health, dict):
        health = {}
    target_url = str(health.get("targetUrl", "")).strip()
    if not target_url:
        payload = health_payload(item, "unknown", "No health probe is configured for this component.")
        HEALTH_CACHE[item_id] = {"expires_at": now + HEALTH_CACHE_TTL_SECONDS, "payload": payload}
        return payload

    expected_codes = normalize_expected_status_codes(health.get("expectedStatusCodes"))
    timeout_seconds = max(1, int(health.get("timeoutSeconds") or 5))
    body_includes = str(health.get("bodyIncludes", "") or "").strip()
    request = urllib.request.Request(
        target_url,
        headers={"Accept": "text/html,application/json;q=0.9,*/*;q=0.8"},
        method="GET",
    )

    status_code = None
    response_body = ""
    checked_at = utc_timestamp()
    try:
        with HEALTHCHECK_OPENER.open(request, timeout=timeout_seconds) as response:
            status_code = int(getattr(response, "status", response.getcode()))
            response_body = response.read(4096).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        status_code = int(exc.code)
        response_body = exc.read(4096).decode("utf-8", "replace")
    except Exception as exc:
        payload = health_payload(item, "down", f"Health check failed: {exc}", checked_at=checked_at)
        HEALTH_CACHE[item_id] = {"expires_at": now + HEALTH_CACHE_TTL_SECONDS, "payload": payload}
        return payload

    if status_code in expected_codes:
        if body_includes and body_includes not in response_body:
            payload = health_payload(
                item,
                "degraded",
                f"Endpoint returned expected HTTP {status_code}, but the configured content marker was not present.",
                checked_at=checked_at,
            )
        else:
            payload = health_payload(
                item,
                "healthy",
                f"Endpoint returned expected HTTP {status_code}.",
                checked_at=checked_at,
            )
    elif status_code >= 500:
        payload = health_payload(item, "down", f"Endpoint returned HTTP {status_code}.", checked_at=checked_at)
    else:
        expected_label = ", ".join(str(code) for code in expected_codes)
        payload = health_payload(
            item,
            "degraded",
            f"Endpoint returned HTTP {status_code}; expected one of {expected_label}.",
            checked_at=checked_at,
        )

    HEALTH_CACHE[item_id] = {"expires_at": now + HEALTH_CACHE_TTL_SECONDS, "payload": payload}
    return payload


def access_control_status():
    directory = directory_status()
    membership_source = str(CONFIG.get("ranger", {}).get("membershipSource", "keycloak") or "keycloak").lower()
    usersync_enabled = bool(CONFIG.get("ranger", {}).get("usersyncEnabled"))
    return {
        "adminEnabled": True,
        "accessControlEnabled": ACCESS_CONTROL_ENABLED,
        "rangerEnabled": bool(CONFIG.get("ranger", {}).get("enabled")),
        "membershipSource": membership_source,
        "usersyncEnabled": usersync_enabled if ACCESS_CONTROL_ENABLED else False,
        "groupAssignmentEnabled": bool(usersync_enabled) if ACCESS_CONTROL_ENABLED else False,
        "userAssignmentEnabled": membership_source == "ranger" and exception_support_enabled() and ACCESS_CONTROL_ENABLED,
        "exceptionSupportEnabled": exception_support_enabled() and ACCESS_CONTROL_ENABLED,
        "ldapEnabled": bool(ldap_config().get("enabled")),
        "ldapReachable": bool(directory.get("ldapReachable")),
        "directoryMessage": ACCESS_CONTROL_DISABLED_MESSAGE if not ACCESS_CONTROL_ENABLED else directory.get("message", ""),
        "auditUrl": CONFIG.get("ranger", {}).get("browserUrl", ""),
        "notice": ACCESS_CONTROL_DISABLED_MESSAGE if not ACCESS_CONTROL_ENABLED else "",
    }


def write_role_membership(role_entry, kind, principal, add_member):
    if kind not in {"user", "group"}:
        raise ApiError(400, "kind must be either user or group.")
    existing = get_role_by_name(role_entry.get("name") or role_entry.get("key"))
    if not existing:
        raise ApiError(404, f"Ranger role {(role_entry.get('name') or role_entry.get('key'))} does not exist yet.")

    users = normalize_role_members(existing.get("users", []))
    groups = normalize_role_members(existing.get("groups", []))
    roles = normalize_role_members(existing.get("roles", []))
    target_members = users if kind == "user" else groups
    target_map = {member["name"]: dict(member) for member in target_members}
    if add_member:
        target_map[principal] = {"name": principal, "isAdmin": False}
    else:
        target_map.pop(principal, None)

    payload = {
        "id": existing["id"],
        "guid": existing.get("guid"),
        "version": existing.get("version"),
        "createdByUser": existing.get("createdByUser"),
        "name": existing.get("name") or role_entry.get("name") or role_entry.get("key"),
        "description": role_entry.get("description", existing.get("description", "")),
        "isEnabled": True,
        "users": normalize_role_members(target_map.values()) if kind == "user" else users,
        "groups": normalize_role_members(target_map.values()) if kind == "group" else groups,
        "roles": roles,
    }
    ranger_request("PUT", role_update_path(existing["id"]), payload, ok=(200,))
    refreshed = get_role_by_name(role_entry.get("name") or role_entry.get("key"))
    return role_view(role_entry, refreshed, load_state_document())


def update_role_membership(role_key, kind, name, add_member):
    membership_source = str(CONFIG.get("ranger", {}).get("membershipSource", "keycloak") or "keycloak").lower()
    if membership_source != "ranger":
        raise ApiError(409, "Live access-control edits are disabled because Keycloak owns platform role membership.")
    if kind == "group" and not bool(CONFIG.get("ranger", {}).get("usersyncEnabled")):
        raise ApiError(409, "LDAP group assignment is unavailable until LDAP and Ranger usersync are enabled.")
    principal = str(name or "").strip()
    if not principal:
        raise ApiError(400, "name must be a non-empty user or group name.")
    if not lookup_directory_principal(kind, principal):
        raise ApiError(404, f"{kind.title()} {principal} was not found in the configured LDAP directory.")
    role_entry = role_entry_for_key(role_key)
    return write_role_membership(role_entry, kind, principal, add_member)


def actor_name(profile):
    return (
        str(profile.get("preferred_username") or "").strip()
        or str(profile.get("email") or "").strip()
        or str(profile.get("sub") or "").strip()
        or "platform-admin"
    )


def create_exception(role_key, payload, profile):
    status = access_control_status()
    if status["membershipSource"] != "ranger":
        raise ApiError(409, "Direct-user exceptions are disabled because Keycloak owns platform role membership.")
    if not status["exceptionSupportEnabled"]:
        raise ApiError(503, "Direct-user exceptions are unavailable because state storage is not configured.")
    user = lookup_directory_principal("user", payload.get("username"))
    if not user:
        raise ApiError(404, f"User {payload.get('username')} was not found in the configured LDAP directory.")
    reason = str(payload.get("reason") or "").strip()
    approval_ref = str(payload.get("approvalRef") or "").strip()
    if not reason or not approval_ref:
        raise ApiError(400, "reason and approvalRef are required.")
    expires_at = normalize_iso8601(payload.get("expiresAt"))
    role_entry = role_entry_for_key(role_key)
    state_document = load_state_document()
    for existing in state_document.get("exceptions", []):
        if (
            str(existing.get("platformRole")) == str(role_key)
            and str(existing.get("username")) == str(user["name"])
            and active_exception(existing)
        ):
            raise ApiError(409, f"User {user['name']} already has an active exception for {role_key}.")

    write_role_membership(role_entry, "user", user["name"], True)
    exception = {
        "id": str(uuid.uuid4()),
        "platformRole": str(role_key),
        "username": user["name"],
        "displayName": str(payload.get("displayName") or user.get("displayName") or user["name"]),
        "email": str(payload.get("email") or user.get("email") or ""),
        "reason": reason,
        "approvalRef": approval_ref,
        "grantedBy": actor_name(profile),
        "createdAt": utc_timestamp(),
        "expiresAt": expires_at,
        "status": "active",
    }
    try:
        state_document.setdefault("exceptions", []).append(exception)
        save_state_document(state_document)
        return exception
    except Exception:
        try:
            write_role_membership(role_entry, "user", user["name"], False)
        except Exception:
            pass
        raise


def remove_exception(role_key, exception_id, profile):
    role_entry = role_entry_for_key(role_key)
    state_document = load_state_document()
    for exception in state_document.get("exceptions", []):
        if str(exception.get("id")) != str(exception_id) or str(exception.get("platformRole")) != str(role_key):
            continue
        if str(exception.get("status", "active")) != "active":
            raise ApiError(404, "That exception is no longer active.")
        write_role_membership(role_entry, "user", exception.get("username"), False)
        exception["status"] = "revoked"
        exception["revokedAt"] = utc_timestamp()
        exception["revokedBy"] = actor_name(profile)
        save_state_document(state_document)
        return exception
    raise ApiError(404, "That direct-user exception was not found.")


def update_exception(role_key, exception_id, payload, profile):
    status = access_control_status()
    if status["membershipSource"] != "ranger":
        raise ApiError(409, "Direct-user exceptions are disabled because Keycloak owns platform role membership.")
    if not status["exceptionSupportEnabled"]:
        raise ApiError(503, "Direct-user exceptions are unavailable because state storage is not configured.")
    reason = str(payload.get("reason") or "").strip()
    approval_ref = str(payload.get("approvalRef") or "").strip()
    if not reason or not approval_ref:
        raise ApiError(400, "reason and approvalRef are required.")
    expires_at = normalize_iso8601(payload.get("expiresAt"))
    state_document = load_state_document()
    for exception in state_document.get("exceptions", []):
        if str(exception.get("id")) != str(exception_id) or str(exception.get("platformRole")) != str(role_key):
            continue
        if str(exception.get("status", "active")) != "active":
            raise ApiError(404, "That exception is no longer active.")
        exception["reason"] = reason
        exception["approvalRef"] = approval_ref
        exception["expiresAt"] = expires_at
        exception["updatedAt"] = utc_timestamp()
        exception["updatedBy"] = actor_name(profile)
        if payload.get("displayName") is not None:
            exception["displayName"] = str(payload.get("displayName") or exception.get("displayName") or exception.get("username") or "")
        if payload.get("email") is not None:
            exception["email"] = str(payload.get("email") or exception.get("email") or "")
        save_state_document(state_document)
        return exception
    raise ApiError(404, "That direct-user exception was not found.")


def reconcile_expired_exceptions():
    state_document = load_state_document()
    changed = False
    for exception in state_document.get("exceptions", []):
        if not active_exception(exception):
            continue
        expires_at = iso_to_epoch(exception.get("expiresAt"))
        if expires_at is None or expires_at > int(time.time()):
            continue
        role_entry = ROLE_CATALOG.get(str(exception.get("platformRole")))
        if role_entry:
            write_role_membership(role_entry, "user", exception.get("username"), False)
        exception["status"] = "expired"
        exception["revokedAt"] = utc_timestamp()
        exception["revokedBy"] = "system:platform-home-reconciler"
        changed = True
    if changed:
        save_state_document(state_document)


class PlatformAdminHandler(BaseHTTPRequestHandler):
    server_version = "platform-home-admin/1.0"

    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        self.handle_request()

    def do_POST(self):
        self.handle_request()

    def do_DELETE(self):
        self.handle_request()

    def handle_request(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        try:
            if path == "/healthz":
                json_response(self, 200, {"status": "ok"})
                return

            if self.command == "GET" and path == "/api/health":
                session = authenticate(self, require_admin=False)
                items = [probe_item_health(item) for item in visible_items_for(session)]
                json_response(self, 200, {"checkedAt": utc_timestamp(), "items": items})
                return

            if self.command == "GET" and path.startswith("/api/launch/"):
                profile = authenticate(self, require_admin=False)
                parts = path.split("/")
                if len(parts) != 4:
                    raise ApiError(404, "Unknown launcher path.")
                launcher_name = urllib.parse.unquote(parts[3])
                json_response(self, 200, resolve_launcher(launcher_name, profile))
                return

            authenticate(self)

            if self.command == "GET" and path in {"/api/admin/status", "/api/admin/access-control/status"}:
                status = access_control_status()
                json_response(
                    self,
                    200,
                    {
                        **status,
                    },
                )
                return

            if self.command == "GET" and path in {"/api/admin/platform-roles", "/api/admin/access-control/roles"}:
                ensure_access_control_enabled()
                json_response(
                    self,
                    200,
                    {
                        "membershipSource": str(CONFIG.get("ranger", {}).get("membershipSource", "keycloak") or "keycloak"),
                        "roles": list_platform_roles(),
                    },
                )
                return

            if self.command == "GET" and path == "/api/admin/principals":
                ensure_access_control_enabled()
                params = urllib.parse.parse_qs(parsed.query or "")
                kind = str((params.get("kind") or [""])[0]).strip().lower()
                query = str((params.get("query") or [""])[0]).strip()
                if kind not in {"user", "group"}:
                    raise ApiError(400, "kind must be either user or group.")
                results = search_directory(kind, query) if query else []
                json_response(self, 200, {"kind": kind, "results": [item["name"] for item in results]})
                return

            if path.startswith("/api/admin/platform-roles/") and path.endswith("/members") and self.command in {"POST", "DELETE"}:
                ensure_access_control_enabled()
                parts = path.split("/")
                if len(parts) != 6:
                    raise ApiError(404, "Unknown admin API path.")
                role_key = urllib.parse.unquote(parts[4])
                payload = read_json(self)
                kind = str(payload.get("kind", "")).strip().lower()
                role = update_role_membership(role_key, kind, payload.get("name"), add_member=self.command == "POST")
                json_response(self, 200, {"role": role})
                return

            if self.command == "GET" and path == "/api/admin/access-control/directory-users":
                ensure_access_control_enabled()
                params = urllib.parse.parse_qs(parsed.query or "")
                query = str((params.get("query") or [""])[0]).strip()
                json_response(self, 200, {"results": search_directory("user", query) if query else []})
                return

            if self.command == "GET" and path == "/api/admin/access-control/directory-groups":
                ensure_access_control_enabled()
                params = urllib.parse.parse_qs(parsed.query or "")
                query = str((params.get("query") or [""])[0]).strip()
                json_response(self, 200, {"results": search_directory("group", query) if query else []})
                return

            if path.startswith("/api/admin/access-control/roles/") and path.endswith("/groups") and self.command in {"POST", "DELETE"}:
                ensure_access_control_enabled()
                parts = path.split("/")
                if len(parts) != 7:
                    raise ApiError(404, "Unknown admin API path.")
                role_key = urllib.parse.unquote(parts[5])
                payload = read_json(self)
                role = update_role_membership(role_key, "group", payload.get("name"), add_member=self.command == "POST")
                json_response(self, 200, {"role": role})
                return

            if path.startswith("/api/admin/access-control/roles/") and path.endswith("/users") and self.command in {"POST", "DELETE"}:
                ensure_access_control_enabled()
                parts = path.split("/")
                if len(parts) != 7:
                    raise ApiError(404, "Unknown admin API path.")
                role_key = urllib.parse.unquote(parts[5])
                payload = read_json(self)
                role = update_role_membership(role_key, "user", payload.get("name"), add_member=self.command == "POST")
                json_response(self, 200, {"role": role})
                return

            if path.startswith("/api/admin/access-control/roles/") and path.endswith("/exceptions") and self.command == "POST":
                ensure_access_control_enabled()
                parts = path.split("/")
                if len(parts) != 7:
                    raise ApiError(404, "Unknown admin API path.")
                role_key = urllib.parse.unquote(parts[5])
                profile = authenticate(self)
                exception = create_exception(role_key, read_json(self), profile)
                json_response(self, 201, {"exception": exception})
                return

            if path.startswith("/api/admin/access-control/roles/") and "/exceptions/" in path and self.command == "PATCH":
                ensure_access_control_enabled()
                parts = path.split("/")
                if len(parts) != 8:
                    raise ApiError(404, "Unknown admin API path.")
                role_key = urllib.parse.unquote(parts[5])
                exception_id = urllib.parse.unquote(parts[7])
                profile = authenticate(self)
                exception = update_exception(role_key, exception_id, read_json(self), profile)
                json_response(self, 200, {"exception": exception})
                return

            if path.startswith("/api/admin/access-control/roles/") and "/exceptions/" in path and self.command == "DELETE":
                ensure_access_control_enabled()
                parts = path.split("/")
                if len(parts) != 8:
                    raise ApiError(404, "Unknown admin API path.")
                role_key = urllib.parse.unquote(parts[5])
                exception_id = urllib.parse.unquote(parts[7])
                profile = authenticate(self)
                exception = remove_exception(role_key, exception_id, profile)
                json_response(self, 200, {"exception": exception})
                return

            raise ApiError(404, "Unknown admin API path.")
        except ApiError as exc:
            json_response(self, exc.status, {"error": exc.message})
        except Exception as exc:
            json_response(self, 500, {"error": str(exc)})


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "reconcile-expired":
        reconcile_expired_exceptions()
        sys.exit(0)
    ThreadingHTTPServer(("0.0.0.0", PORT), PlatformAdminHandler).serve_forever()
