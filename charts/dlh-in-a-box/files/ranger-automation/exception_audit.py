import base64
import datetime
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

CONFIG_PATH = "/opt/ranger-automation/bootstrap-config.json"
RANGER_URL = os.environ["RANGER_URL"].rstrip("/")
RANGER_PASSWORD = os.environ["RANGER_ADMIN_PASSWORD"]
METADATA_MARKER = "EXCEPTION_METADATA="


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def request(method, path, payload=None, ok=(200, 201), parse_json=True):
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
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = response.read().decode("utf-8")
            if not parse_json:
                return data
            return json.loads(data) if data else None
    except urllib.error.HTTPError as exc:
        if exc.code in ok:
            data = exc.read().decode("utf-8")
            if not parse_json:
                return data
            return json.loads(data) if data else None
        raise


def wait_for_ranger():
    deadline = time.time() + 600
    while time.time() < deadline:
        try:
            request("GET", "/login.jsp", ok=(200,), parse_json=False)
            return
        except Exception:
            time.sleep(5)
    raise RuntimeError("Timed out waiting for Ranger Admin")


def list_roles():
    roles = []
    start_index = 0
    page_size = 200
    while True:
        page = request(
            "GET",
            f"/service/public/v2/api/roles?startIndex={start_index}&pageSize={page_size}",
            ok=(200,),
        ) or []
        roles.extend(page)
        if len(page) < page_size:
            break
        start_index += page_size
    return roles


def list_role_names(service_name):
    del service_name
    return [str(role.get("name", "")) for role in list_roles() if str(role.get("name", "")).strip()]


def get_role(service_name, role_name):
    del service_name
    for role in list_roles():
        if str(role.get("name", "")) == str(role_name):
            return role
    return None


def delete_role(service_name, role_name):
    existing = get_role(service_name, role_name)
    if not existing:
        return
    path = "/service/public/v2/api/roles/" + urllib.parse.quote(str(existing["id"]), safe="")
    request("DELETE", path, ok=(204, 404))


def parse_metadata(description):
    if not description or METADATA_MARKER not in description:
        return None
    raw = description.split(METADATA_MARKER, 1)[1].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def main():
    wait_for_ranger()
    config = load_config()
    audit_cfg = config["ranger"].get("exceptionRoleAudit", {}) or {}
    if not audit_cfg.get("enabled", True):
        print("Exception role audit disabled; exiting.")
        return

    service_name = config["ranger"]["serviceName"]
    prefix = audit_cfg.get("prefix", "exception-")
    grace_days = int(audit_cfg.get("gracePeriodDays", 7))
    delete_expired = bool(audit_cfg.get("deleteExpired", True))
    log_undocumented = bool(audit_cfg.get("logUndocumented", True))
    today = datetime.date.today()

    for role_name in sorted(name for name in list_role_names(service_name) if str(name).startswith(prefix)):
        role = get_role(service_name, role_name) or {}
        metadata = parse_metadata(role.get("description", ""))
        if not metadata:
            if log_undocumented:
                print(f"WARNING: {role_name} is missing structured exception metadata.")
            continue

        expires_at_raw = metadata.get("expiresAt", "")
        try:
            expires_at = datetime.date.fromisoformat(expires_at_raw)
        except ValueError:
            print(f"WARNING: {role_name} has invalid expiresAt metadata: {expires_at_raw!r}")
            continue

        if today <= expires_at:
            continue

        grace_deadline = expires_at + datetime.timedelta(days=grace_days)
        if today <= grace_deadline:
            print(
                f"WARNING: {role_name} expired on {expires_at.isoformat()} but is still within "
                f"the {grace_days}-day grace period."
            )
            continue

        if delete_expired:
            delete_role(service_name, role_name)
            print(f"Deleted expired exception role: {role_name}")
        else:
            print(
                f"WARNING: {role_name} expired on {expires_at.isoformat()} and exceeded the "
                f"{grace_days}-day grace period."
            )


if __name__ == "__main__":
    main()
