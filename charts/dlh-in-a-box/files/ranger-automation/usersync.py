import base64
import json
import os
import ssl
import time
import urllib.error
import urllib.request
import urllib.parse

from ldap3 import BASE, SUBTREE, Connection, Server, Tls
from ldap3.core.exceptions import LDAPBindError

CONFIG_PATH = "/opt/ranger-automation/bootstrap-config.json"
RANGER_URL = os.environ["RANGER_URL"].rstrip("/")
RANGER_PASSWORD = os.environ["RANGER_ADMIN_PASSWORD"]
LDAP_BIND_PASSWORD = os.environ["LDAP_BIND_PASSWORD"]
REST_CSRF_HEADER = None
REST_CSRF_TOKEN = None
REST_CSRF_METHODS_TO_IGNORE = {"GET", "OPTIONS", "HEAD", "TRACE"}
REST_CSRF_READY = False


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def ranger_headers():
    return {
        "Authorization": "Basic "
        + base64.b64encode(f"admin:{RANGER_PASSWORD}".encode("utf-8")).decode("ascii"),
        "Accept": "application/json",
    }


def ensure_csrf():
    global REST_CSRF_HEADER, REST_CSRF_TOKEN, REST_CSRF_METHODS_TO_IGNORE, REST_CSRF_READY
    if REST_CSRF_READY:
        return
    req = urllib.request.Request(
        f"{RANGER_URL}/service/plugins/csrfconf",
        headers=ranger_headers(),
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8") or "{}")
    if payload.get("ranger.rest-csrf.enabled"):
        REST_CSRF_HEADER = str(payload.get("ranger.rest-csrf.custom-header") or "").strip()
        REST_CSRF_TOKEN = str(payload.get("_csrfToken") or "").strip()
        ignored = str(payload.get("ranger.rest-csrf.methods-to-ignore") or "").strip()
        if ignored:
            REST_CSRF_METHODS_TO_IGNORE = {method.strip().upper() for method in ignored.split(",") if method.strip()}
    REST_CSRF_READY = True


def ranger_request(method, path, payload=None, ok=(200, 201), parse_json=True):
    url = f"{RANGER_URL}{path}"
    headers = ranger_headers()
    if method.upper() not in REST_CSRF_METHODS_TO_IGNORE:
        ensure_csrf()
        if REST_CSRF_HEADER:
            headers[REST_CSRF_HEADER] = REST_CSRF_TOKEN or '""'
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
            ranger_request("GET", "/login.jsp", ok=(200,), parse_json=False)
            return
        except Exception:
            time.sleep(5)
    raise RuntimeError("Timed out waiting for Ranger Admin")


def attr_value(entry, name):
    try:
        return str(entry[name].value or "")
    except Exception:
        return ""


def normalize_names(values):
    seen = set()
    normalized = []
    for value in values or []:
        name = str(value or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        normalized.append(name)
    return normalized


def list_users():
    users = []
    start_index = 0
    page_size = 200
    while True:
        payload = ranger_request(
            "GET",
            f"/service/xusers/users?startIndex={start_index}&pageSize={page_size}",
            ok=(200,),
        ) or {}
        batch = payload.get("vXUsers", []) or []
        if not batch:
            break
        users.extend(batch)
        total_count = int(payload.get("totalCount", len(users)) or len(users))
        if len(users) >= total_count:
            break
        start_index += len(batch)
    return users


def build_synced_user(username, first_name="", last_name="", email_address=""):
    username = str(username or "").strip()
    first_name = str(first_name or "").strip() or username
    last_name = str(last_name or "").strip() or "User"
    email_address = str(email_address or "").strip()
    return {
        "name": username,
        "firstName": first_name,
        "lastName": last_name,
        "emailAddress": email_address,
        "status": 1,
        "isVisible": 1,
        "userSource": 1,
        "userRoleList": ["ROLE_USER"],
        "syncSource": "LDAP",
    }


def search_user_by_dn(conn, ldap_cfg, member_dn):
    conn.search(
        member_dn,
        "(objectClass=*)",
        search_scope=BASE,
        attributes=[
            ldap_cfg["usernameAttribute"],
            ldap_cfg["firstNameAttribute"],
            ldap_cfg["lastNameAttribute"],
            ldap_cfg["emailAttribute"],
        ],
    )
    if not conn.entries:
        return None
    return conn.entries[0]


def synced_user_from_entry(entry, ldap_cfg):
    username = attr_value(entry, ldap_cfg["usernameAttribute"])
    if not username:
        return None, None
    return username, build_synced_user(
        username,
        first_name=attr_value(entry, ldap_cfg["firstNameAttribute"]),
        last_name=attr_value(entry, ldap_cfg["lastNameAttribute"]),
        email_address=attr_value(entry, ldap_cfg["emailAttribute"]),
    )


def desired_usernames(config, synced_ldap_users):
    desired = set(normalize_names(synced_ldap_users))

    service_username = str((config.get("ranger") or {}).get("serviceUsername") or "").strip()
    if service_username:
        desired.add(service_username)
    for policy in (config.get("ranger") or {}).get("baselinePolicies", []) or []:
        for key in [
            "policyItems",
            "denyPolicyItems",
            "allowExceptions",
            "denyExceptions",
            "dataMaskPolicyItems",
            "rowFilterPolicyItems",
        ]:
            for item in policy.get(key, []) or []:
                desired.update(normalize_names(item.get("users", [])))

    return desired


def protected_usernames(config):
    ranger_cfg = config.get("ranger") or {}
    protected = {"admin", "rangerusersync", "rangertagsync"}
    protected.update(normalize_names(ranger_cfg.get("serviceAdminUsers", [])))
    protected.update(normalize_names(ranger_cfg.get("superUsers", [])))
    return {username for username in protected if username}


def delete_user(user_id):
    ranger_request(
        "DELETE",
        f"/service/xusers/secure/users/id/{user_id}?forceDelete=true",
        ok=(200, 204, 404),
        parse_json=False,
    )


def prune_unexpected_users(config, synced_ldap_users):
    keep_usernames = desired_usernames(config, synced_ldap_users)
    protected = protected_usernames(config)
    stale_users = []
    for user in list_users():
        username = str(user.get("name") or "").strip()
        if not username:
            continue
        if username in protected:
            continue
        if int(user.get("userSource", 1) or 1) == 0:
            continue
        if username in keep_usernames:
            continue
        stale_users.append(user)

    if not stale_users:
        print("No stale Ranger users found.")
        return

    deleted = []
    failed = []
    for user in stale_users:
        username = str(user.get("name") or "").strip()
        try:
            delete_user(user["id"])
            deleted.append(username)
        except urllib.error.HTTPError as exc:
            failed.append((username, exc.code, exc.read().decode("utf-8", errors="replace")))

    if deleted:
        print("Deleted stale Ranger users: " + ", ".join(sorted(name for name in deleted if name)))
    if failed:
        for username, status_code, body in failed:
            print(f"WARNING: unable to delete stale Ranger user {username}: HTTP {status_code} {body}")


def sync(config):
    ldap_cfg = config["ldap"]
    parsed = urllib.parse.urlparse(ldap_cfg["url"])
    use_ssl = parsed.scheme == "ldaps"
    host = parsed.hostname or ldap_cfg["url"]
    port = parsed.port or (636 if use_ssl else 389)
    tls = None
    if use_ssl:
        trusted_ca_path = ldap_cfg.get("trustedCaPath")
        if ldap_cfg.get("allowInsecure", False):
            tls = Tls(validate=ssl.CERT_NONE)
        elif trusted_ca_path and os.path.exists(trusted_ca_path):
            tls = Tls(validate=ssl.CERT_REQUIRED, ca_certs_file=trusted_ca_path)
        else:
            tls = Tls(validate=ssl.CERT_REQUIRED)
    server = Server(host, port=port, use_ssl=use_ssl, tls=tls, get_info=None)
    bind_dn = str(ldap_cfg.get("bindDn") or "").strip()
    if bind_dn and LDAP_BIND_PASSWORD:
        try:
            conn = Connection(server, user=bind_dn, password=LDAP_BIND_PASSWORD, auto_bind=True)
        except LDAPBindError:
            print(f"LDAP bind failed for {bind_dn}; falling back to anonymous read", flush=True)
            conn = Connection(server, auto_bind=True)
    else:
        conn = Connection(server, auto_bind=True)
    group_name_attribute = ldap_cfg["groupNameAttribute"]
    group_search_filter = ldap_cfg["groupSearchFilter"]

    conn.search(
        ldap_cfg["groupBaseDn"],
        group_search_filter,
        search_scope=SUBTREE,
        attributes=[
            group_name_attribute,
            ldap_cfg["groupSearchMemberAttribute"],
        ],
    )

    groups = {}
    users = {}

    for group_entry in conn.entries:
        group_name = attr_value(group_entry, group_name_attribute)
        if not group_name:
            continue
        raw_members = []
        try:
            raw_members = list(group_entry[ldap_cfg["groupSearchMemberAttribute"]].values)
        except Exception:
            raw_members = []

        member_names = set()
        for member_dn in raw_members:
            member_dn = str(member_dn)
            if not member_dn:
                continue
            if "=" in member_dn and "," in member_dn:
                user_entry = search_user_by_dn(conn, ldap_cfg, member_dn)
                if user_entry is None:
                    continue
                username, synced_user = synced_user_from_entry(user_entry, ldap_cfg)
                if not username or not synced_user:
                    continue
                member_names.add(username)
                users[username] = synced_user
            else:
                member_names.add(member_dn)
                users.setdefault(member_dn, build_synced_user(member_dn))

        groups[group_name] = sorted(member_names)

    if users:
        ranger_request(
            "POST",
            "/service/xusers/ugsync/users",
            {"vXUsers": list(users.values())},
            ok=(200, 201),
        )

    if groups:
        ranger_request(
            "POST",
            "/service/xusers/ugsync/groups",
            {
                "vXGroups": [
                    {
                        "name": group_name,
                        "description": "Synced from LDAP/AD",
                        "isVisible": 1,
                        "groupSource": 1,
                        "syncSource": "LDAP",
                    }
                    for group_name in sorted(groups)
                ]
            },
            ok=(200, 201),
        )

    current = ranger_request("GET", "/service/xusers/ugsync/groupusers", ok=(200,)) or {}
    deltas = []
    for group_name, desired_members in groups.items():
        current_members = set(current.get(group_name, []))
        desired_members = set(desired_members)
        add_users = sorted(desired_members - current_members)
        del_users = sorted(current_members - desired_members)
        if add_users or del_users:
            deltas.append(
                {
                    "groupName": group_name,
                    "addUsers": add_users,
                    "delUsers": del_users,
                }
            )

    if deltas:
        ranger_request("POST", "/service/xusers/ugsync/groupusers", deltas, ok=(200, 201))

    prune_unexpected_users(config, list(users))


def main():
    wait_for_ranger()
    sync(load_config())


if __name__ == "__main__":
    main()
