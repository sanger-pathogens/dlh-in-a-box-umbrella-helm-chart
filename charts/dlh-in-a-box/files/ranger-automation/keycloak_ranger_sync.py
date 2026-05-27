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
    return payload["access_token"]


def keycloak_request(config, token, method, path, payload=None, ok=(200, 201, 204)):
    base_url = config["identity"]["keycloak"]["adminUrl"].rstrip("/")
    url = f"{base_url}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
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
    return keycloak_request(
        config,
        token,
        "GET",
        f"{path}{delimiter}first={first}&max={max_results}",
        ok=(200,),
    ) or []


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


def should_sync_user(username, email, enabled):
    if not enabled:
        return False
    if username in {
        "admin",
        "keyadmin",
        "trino",
        "trino-admin",
        "cloudbeaver-service",
        "superset-service",
        "service-account-prefect-automation",
        "{OWNER}",
        "{USER}",
    }:
        return False
    if (
        username.startswith("codex-")
        or username.startswith("service-account-")
        or username.endswith("-service")
        or username.endswith("-test-sync")
    ):
        return False
    if email.endswith(".example.invalid"):
        return False
    return True


def normalize_keycloak_user(config, token, user):
    keycloak = config["identity"]["keycloak"]
    if keycloak.get("requireEmailVerification", False):
        return False, False

    required_actions = [action for action in user.get("requiredActions") or [] if action != "VERIFY_EMAIL"]
    email_verified = bool(user.get("emailVerified", False))
    verify_email_required = "VERIFY_EMAIL" in (user.get("requiredActions") or [])

    if email_verified and not verify_email_required and required_actions == (user.get("requiredActions") or []):
        return False, False

    updated = dict(user)
    updated["emailVerified"] = True
    updated["requiredActions"] = required_actions
    realm = keycloak["realm"]
    keycloak_request(
        config,
        token,
        "PUT",
        f"/admin/realms/{realm}/users/{user['id']}",
        updated,
    )

    logged_out = False
    try:
        keycloak_request(
            config,
            token,
            "POST",
            f"/admin/realms/{realm}/users/{user['id']}/logout",
            ok=(204,),
        )
        logged_out = True
    except Exception as exc:
        print(
            f"WARNING: normalized Keycloak user {user.get('username') or user['id']} "
            f"but failed to clear stale sessions: {exc}",
            file=sys.stderr,
        )

    return True, logged_out


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
        "userRoleList": ["ROLE_USER"],
        "isVisible": 1,
        "userSource": 1,
        "syncSource": "KEYCLOAK_LOCAL",
    }


def normalize_names(items):
    return sorted({str(item).strip() for item in (items or []) if str(item).strip()})


def role_member(name, is_admin=False):
    return {"name": str(name), "isAdmin": bool(is_admin)}


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
        members[name] = members.get(name, False) or is_admin
    return [role_member(name, members[name]) for name in sorted(members)]


def access_model_role_names(config):
    access_model = config.get("accessModel") or {}
    role_names = []
    for role_name in sorted((access_model.get("builtinRoles") or {}).keys()):
        name = str(role_name or "").strip()
        if name:
            role_names.append(name)
    for role_name in sorted((access_model.get("additionalRoles") or {}).keys()):
        raw_role = (access_model.get("additionalRoles") or {}).get(role_name) or {}
        if isinstance(raw_role, dict) and raw_role.get("enabled") is False:
            continue
        name = str(role_name or "").strip()
        if name:
            role_names.append(name)
    return normalize_names(role_names)


def configured_group_names(config):
    access_model = config.get("accessModel") or {}
    return normalize_names((access_model.get("groupRoleMappings") or {}).keys())


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


def list_ranger_groups():
    groups = []
    start_index = 0
    page_size = 200
    while True:
        payload = ranger_request(
            "GET",
            f"/service/xusers/groups?startIndex={start_index}&pageSize={page_size}",
            ok=(200,),
        ) or {}
        batch = payload.get("vXGroups", []) or []
        if not batch:
            break
        groups.extend(batch)
        total_count = int(payload.get("totalCount", len(groups)) or len(groups))
        if len(groups) >= total_count:
            break
        start_index += len(batch)
    return groups


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
        roles.extend(page)
        if len(page) < page_size:
            break
        start_index += page_size
    return roles


def get_role(role_name):
    for role in list_roles():
        if str(role.get("name", "")).strip() == str(role_name).strip():
            return role
    return None


def role_create_path(create_missing_principals):
    create_missing = "true" if create_missing_principals else "false"
    return f"/service/public/v2/api/roles?createNonExistUserGroup={create_missing}"


def role_update_path(role_id, create_missing_principals):
    create_missing = "true" if create_missing_principals else "false"
    return f"/service/public/v2/api/roles/{role_id}?createNonExistUserGroup={create_missing}"


def upsert_role(role, create_missing_principals):
    payload = {
        "name": role["name"],
        "description": role.get("description", ""),
        "isEnabled": True,
        "users": normalize_role_members(role.get("users", [])),
        "groups": normalize_role_members(role.get("groups", [])),
        "roles": normalize_role_members(role.get("roles", [])),
    }
    existing = get_role(role["name"])
    if existing:
        payload["id"] = existing["id"]
        payload["guid"] = existing.get("guid")
        payload["version"] = existing.get("version")
        payload["createdByUser"] = existing.get("createdByUser")
        ranger_request("PUT", role_update_path(existing["id"], create_missing_principals), payload, ok=(200,))
    else:
        ranger_request("POST", role_create_path(create_missing_principals), payload, ok=(200, 201))


def keycloak_group_by_name(config, token, group_name):
    realm = config["identity"]["keycloak"]["realm"]
    groups = keycloak_request(
        config,
        token,
        "GET",
        f"/admin/realms/{realm}/groups?search={urllib.parse.quote(group_name)}&max=1000",
        ok=(200,),
    ) or []

    def walk(items):
        for item in items or []:
            yield item
            yield from walk(item.get("subGroups") or [])

    for group in walk(groups):
        if str(group.get("name", "")).strip() == group_name:
            return group
    return None


def keycloak_role_exists(config, token, role_name):
    realm = config["identity"]["keycloak"]["realm"]
    encoded = urllib.parse.quote(role_name, safe="")
    payload = keycloak_request(
        config,
        token,
        "GET",
        f"/admin/realms/{realm}/roles/{encoded}",
        ok=(200, 404),
    )
    return isinstance(payload, dict) and str(payload.get("name") or "").strip() == role_name


def keycloak_role_users(config, token, role_name):
    realm = config["identity"]["keycloak"]["realm"]
    encoded = urllib.parse.quote(role_name, safe="")
    users = keycloak_list(config, token, f"/admin/realms/{realm}/roles/{encoded}/users")
    result = []
    for user in users:
        username = str(user.get("username") or "").strip()
        email = str(user.get("email") or "").strip()
        enabled = bool(user.get("enabled", True))
        if username and should_sync_user(username, email, enabled):
            result.append(username)
    return normalize_names(result)


def keycloak_role_groups(config, token, role_name):
    realm = config["identity"]["keycloak"]["realm"]
    encoded = urllib.parse.quote(role_name, safe="")
    groups = keycloak_list(config, token, f"/admin/realms/{realm}/roles/{encoded}/groups")
    result = []
    for group in groups:
        name = str(group.get("name") or "").strip()
        group_id = str(group.get("id") or "").strip()
        if name:
            result.append({"name": name, "id": group_id})
    return result


def keycloak_group_members(config, token, group_id, eligible_users):
    realm = config["identity"]["keycloak"]["realm"]
    members = keycloak_list(config, token, f"/admin/realms/{realm}/groups/{group_id}/members")
    result = []
    for user in members:
        username = str(user.get("username") or "").strip()
        if username and username in eligible_users:
            result.append(username)
    return normalize_names(result)


def keycloak_users(config, token):
    realm = config["identity"]["keycloak"]["realm"]
    return keycloak_list(config, token, f"/admin/realms/{realm}/users")


def keycloak_role_memberships(config, token, role_names):
    memberships = {}
    groups_by_name = {}
    for role_name in role_names:
        if not keycloak_role_exists(config, token, role_name):
            print(f"WARNING: Keycloak realm role {role_name} does not exist; skipping Ranger role sync.")
            continue
        role_groups = keycloak_role_groups(config, token, role_name)
        groups = normalize_names(group["name"] for group in role_groups)
        for group in role_groups:
            if group.get("id"):
                groups_by_name[group["name"]] = group
        memberships[role_name] = {
            "users": keycloak_role_users(config, token, role_name),
            "groups": groups,
        }
    return memberships, groups_by_name


def sync_ranger_users(users):
    if not users:
        return 0
    existing_names = {
        str(user.get("name") or "").strip()
        for user in list_ranger_users()
        if str(user.get("name") or "").strip()
    }
    missing = {
        username: user
        for username, user in users.items()
        if username not in existing_names
    }
    if not missing:
        return 0
    ranger_request("POST", "/service/xusers/ugsync/users", {"vXUsers": list(missing.values())}, ok=(200, 201))
    return len(missing)


def sync_ranger_groups(group_members):
    if not group_members:
        return 0
    existing_names = {
        str(group.get("name") or "").strip()
        for group in list_ranger_groups()
        if str(group.get("name") or "").strip()
    }
    missing_names = sorted(set(group_members) - existing_names)
    if not missing_names:
        return 0
    ranger_request(
        "POST",
        "/service/xusers/ugsync/groups",
        {
            "vXGroups": [
                {
                    "name": group_name,
                    "description": "Synced from Keycloak",
                    "isVisible": 1,
                    "groupSource": 1,
                    "syncSource": "KEYCLOAK_LOCAL",
                }
                for group_name in missing_names
            ]
        },
        ok=(200, 201),
    )
    return len(missing_names)


def sync_ranger_group_memberships(group_members):
    if not group_members:
        return 0
    current = ranger_request("GET", "/service/xusers/ugsync/groupusers", ok=(200,)) or {}
    deltas = []
    for group_name, desired_members in group_members.items():
        current_members = set(current.get(group_name, []))
        desired_members = set(desired_members)
        add_users = sorted(desired_members - current_members)
        del_users = sorted(current_members - desired_members)
        if add_users or del_users:
            deltas.append({"groupName": group_name, "addUsers": add_users, "delUsers": del_users})
    if deltas:
        ranger_request("POST", "/service/xusers/ugsync/groupusers", deltas, ok=(200, 201))
    return len(deltas)


def sync_local_principals(config, token, role_group_index):
    users = {}
    normalized_count = 0
    logged_out_count = 0
    for user in keycloak_users(config, token):
        username = str(user.get("username") or "").strip()
        email = str(user.get("email") or "").strip()
        enabled = bool(user.get("enabled", True))
        if not username or not should_sync_user(username, email, enabled):
            continue

        normalized, logged_out = normalize_keycloak_user(config, token, user)
        if normalized:
            normalized_count += 1
        if logged_out:
            logged_out_count += 1

        users[username] = build_synced_user(
            username,
            user.get("firstName") or username,
            user.get("lastName") or "User",
            email,
        )

    group_index = dict(role_group_index)
    for group_name in configured_group_names(config):
        if group_name in group_index:
            continue
        group = keycloak_group_by_name(config, token, group_name)
        if group and group.get("id"):
            group_index[group_name] = {"name": group_name, "id": str(group["id"])}
        else:
            print(f"WARNING: configured Keycloak group {group_name} does not exist; skipping Ranger group sync.")

    group_members = {}
    for group_name, group in sorted(group_index.items()):
        group_id = str(group.get("id") or "").strip()
        if group_id:
            group_members[group_name] = keycloak_group_members(config, token, group_id, users)

    synced_users = sync_ranger_users(users)
    synced_groups = sync_ranger_groups(group_members)
    group_deltas = sync_ranger_group_memberships(group_members)
    return synced_users, synced_groups, group_deltas, normalized_count, logged_out_count


def sync_ranger_roles(memberships, create_missing_principals):
    synced = 0
    for role_name in sorted(memberships):
        members = memberships[role_name]
        upsert_role(
            {
                "name": role_name,
                "description": f"Synced from Keycloak realm role {role_name}.",
                "users": members.get("users", []),
                "groups": members.get("groups", []),
                "roles": [],
            },
            create_missing_principals,
        )
        synced += 1
    return synced


def sync():
    config = load_config()
    role_names = access_model_role_names(config)
    if not role_names:
        print("No platform access-model roles are configured; skipping Ranger Keycloak sync.")
        return

    wait_for_ranger()
    token = keycloak_token(config)
    memberships, role_group_index = keycloak_role_memberships(config, token, role_names)
    local_mode = config["identity"].get("directoryMode") == "keycloakLocal"

    synced_users = 0
    synced_groups = 0
    group_deltas = 0
    normalized_count = 0
    logged_out_count = 0
    if local_mode:
        (
            synced_users,
            synced_groups,
            group_deltas,
            normalized_count,
            logged_out_count,
        ) = sync_local_principals(config, token, role_group_index)

    synced_roles = sync_ranger_roles(memberships, create_missing_principals=local_mode)
    print(
        "Synced Keycloak realm roles to Ranger "
        f"({synced_roles} roles, local principals: {synced_users} users, {synced_groups} groups, "
        f"{group_deltas} group membership deltas, {normalized_count} Keycloak accounts normalized, "
        f"{logged_out_count} stale Keycloak sessions cleared)."
    )


if __name__ == "__main__":
    sync()
