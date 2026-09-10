import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

CONFIG_PATH = "/opt/ranger-automation/bootstrap-config.json"
RANGER_URL = os.environ["RANGER_URL"].rstrip("/")
RANGER_PASSWORD = os.environ["RANGER_ADMIN_PASSWORD"]
KEYCLOAK_ADMIN_PASSWORD = os.environ["KEYCLOAK_ADMIN_PASSWORD"]
RANGER_SYNC_SOURCE = "Keycloak"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def wait_for_ranger():
    deadline = time.time() + 600
    while time.time() < deadline:
        try:
            ranger_request("GET", "/login.jsp", ok=(200,), parse_json=False)
            return
        except Exception:
            time.sleep(5)
    raise RuntimeError("Timed out waiting for Ranger Admin")


def ranger_request(method, path, payload=None, ok=(200, 201), parse_json=True):
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
        data = exc.read().decode("utf-8")
        if exc.code in ok:
            if not parse_json:
                return data
            return json.loads(data) if data else None
        exc.ranger_body = data
        if data:
            print(f"Ranger API {method} {path} failed with HTTP {exc.code}: {data}", file=sys.stderr)
        raise


def keycloak_token(config):
    keycloak = config["identity"]["keycloak"]
    params = urllib.parse.urlencode(
        {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": keycloak.get("adminUsername", "admin"),
            "password": KEYCLOAK_ADMIN_PASSWORD,
        }
    ).encode("utf-8")
    url = f"{keycloak['adminUrl'].rstrip('/')}/realms/master/protocol/openid-connect/token"
    req = urllib.request.Request(
        url,
        data=params,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    token = payload.get("access_token") if isinstance(payload, dict) else None
    if not token:
        raise RuntimeError("Keycloak token response did not include an access_token; refusing to sync")
    return token


def keycloak_get(config, token, path, ok=(200,)):
    """Read-only GET against the Keycloak Admin API."""
    base_url = config["identity"]["keycloak"]["adminUrl"].rstrip("/")
    url = f"{base_url}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = response.read().decode("utf-8")
            return json.loads(data) if data else None
    except urllib.error.HTTPError as exc:
        data = exc.read().decode("utf-8")
        if exc.code in ok:
            if not data:
                return None
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return None
        exc.keycloak_body = data
        raise


def keycloak_get_page(config, token, path, first=0, max_results=200):
    delimiter = "&" if "?" in path else "?"
    full_path = f"{path}{delimiter}first={first}&max={max_results}"
    page = keycloak_get(config, token, full_path, ok=(200,))
    if page is None:
        return []
    if not isinstance(page, list):
        raise RuntimeError(
            f"Unexpected Keycloak response for {full_path}: expected a list, got {type(page).__name__}"
        )
    return page


def keycloak_list(config, token, path):
    results = []
    first = 0
    max_results = 200
    while True:
        page = keycloak_get_page(config, token, path, first=first, max_results=max_results)
        results.extend(page)
        if len(page) < max_results:
            break
        first += len(page)
    return results


def should_sync_user(enabled):
    return bool(enabled)


def build_synced_user(username, first_name="", last_name="", email_address=""):
    username = str(username or "").strip()
    first_name = str(first_name or "").strip() or username
    last_name = str(last_name or "").strip() or "User"
    email_address = str(email_address or "").strip()
    user = {
        "name": username,
        "firstName": first_name,
        "lastName": last_name,
        "status": 1,
        "userRoleList": ["ROLE_USER"],
        "isVisible": 1,
        "userSource": 1,
        "syncSource": RANGER_SYNC_SOURCE,
    }
    if email_address:
        # Ranger rejects the whole batch with a 400 if emailAddress is present but
        # empty (e.g. a service-account user, which has no email in Keycloak);
        # omitting the field entirely is accepted.
        user["emailAddress"] = email_address
    return user


def normalize_names(items):
    return sorted({str(item).strip() for item in (items or []) if str(item).strip()})


def list_ranger_users():
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


def delete_ranger_user(user_id):
    ranger_request(
        "DELETE",
        f"/service/xusers/secure/users/id/{user_id}?forceDelete=true",
        ok=(200, 204, 404),
        parse_json=False,
    )


def keycloak_clients(config, token):
    realm = config["identity"]["keycloak"]["realm"]
    return keycloak_list(config, token, f"/admin/realms/{realm}/clients")


def keycloak_service_account_user(config, token, client_uuid):
    realm = config["identity"]["keycloak"]["realm"]
    user = keycloak_get(
        config,
        token,
        f"/admin/realms/{realm}/clients/{client_uuid}/service-account-user",
        ok=(200, 404),
    )
    if user is not None and not isinstance(user, dict):
        raise RuntimeError(
            f"Unexpected Keycloak response for client {client_uuid} service-account-user: "
            f"expected an object, got {type(user).__name__}"
        )
    return user


def keycloak_service_account_users(config, token):
    users = []
    for client in keycloak_clients(config, token):
        if not client.get("serviceAccountsEnabled"):
            continue
        user = keycloak_service_account_user(config, token, client["id"])
        if user is not None:
            users.append(user)
    return users


def keycloak_users(config, token):
    # A plain GET /users listing silently omits service-account users (Keycloak
    # hides them from the admin console's default Users page); they must be
    # fetched individually via each service-account-enabled client instead.
    realm = config["identity"]["keycloak"]["realm"]
    human_users = keycloak_list(config, token, f"/admin/realms/{realm}/users")
    return human_users + keycloak_service_account_users(config, token)


def sync_ranger_users(desired_users):
    existing_by_name = {
        str(user.get("name") or "").strip(): user
        for user in list_ranger_users()
        if str(user.get("name") or "").strip()
    }

    missing = {
        username: user
        for username, user in desired_users.items()
        if username not in existing_by_name
    }
    if missing:
        ranger_request("POST", "/service/xusers/ugsync/users", {"vXUsers": list(missing.values())}, ok=(200, 201))

    removed = []
    for username, user in existing_by_name.items():
        if username in desired_users:
            continue
        if str(user.get("syncSource") or "").strip() != RANGER_SYNC_SOURCE:
            continue
        delete_ranger_user(user["id"])
        removed.append(username)

    return len(missing), len(removed)


def sync_local_principals(config, token):
    users = {}
    for user in keycloak_users(config, token):
        username = str(user.get("username") or "").strip()
        email = str(user.get("email") or "").strip()
        enabled = bool(user.get("enabled", True))
        if not username or not should_sync_user(enabled):
            continue

        users[username] = build_synced_user(
            username,
            user.get("firstName") or username,
            user.get("lastName") or "User",
            email,
        )

    return sync_ranger_users(users)


def sync():
    config = load_config()
    wait_for_ranger()
    token = keycloak_token(config)
    local_mode = config["identity"].get("directoryMode") == "keycloakLocal"

    added, removed = 0, 0
    if local_mode:
        added, removed = sync_local_principals(config, token)

    print(f"Synced Keycloak users to Ranger ({added} added, {removed} removed).")


if __name__ == "__main__":
    sync()
