import base64
import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CONFIG_PATH = "/opt/platform-home-api/admin-config.json"
PORT = int(os.environ.get("PORT", "18080"))
USERINFO_URL = os.environ.get("IDENTITY_USERINFO_URL", "")
EXPECTED_ISSUER = os.environ.get("IDENTITY_EXPECTED_ISSUER", "")
ROLES_CLAIM = os.environ.get("OIDC_ROLES_CLAIM", "platform_roles")
ADMIN_ROLES = [
    item.strip()
    for item in os.environ.get("PLATFORM_ADMIN_ROLES", "platform-admin").split(",")
    if item.strip()
]
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
HEALTH_CACHE = {}
HEALTH_CACHE_TTL_SECONDS = max(
    15,
    int(CONFIG.get("health", {}).get("refreshIntervalSeconds") or CACHE_TTL_SECONDS),
)
HTTPS_CONTEXT = ssl._create_unverified_context()


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

    if mode == "minio-sso":
        internal_api_url = str(launcher.get("internalApiUrl") or "").rstrip("/")
        target_url = str(launcher.get("targetUrl") or "").strip()
        if not internal_api_url:
            raise ApiError(500, "The MinIO launcher is missing its internal API URL.")
        response = launcher_request(f"{internal_api_url}/api/v1/login")
        redirect_rules = response.get("redirectRules")
        if not isinstance(redirect_rules, list):
            redirect_rules = []
        for rule in redirect_rules:
            if not isinstance(rule, dict):
                continue
            redirect_url = str(rule.get("redirect") or "").strip()
            if redirect_url:
                return {"mode": "redirect", "url": redirect_url}
        if target_url:
            return {"mode": "redirect", "url": target_url}
        raise ApiError(502, "MinIO did not return an OIDC redirect URL.")

    raise ApiError(500, f"Unsupported launcher mode: {mode}")


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

            raise ApiError(404, "Unknown admin API path.")
        except ApiError as exc:
            json_response(self, exc.status, {"error": exc.message})
        except Exception as exc:
            json_response(self, 500, {"error": str(exc)})


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), PlatformAdminHandler).serve_forever()
