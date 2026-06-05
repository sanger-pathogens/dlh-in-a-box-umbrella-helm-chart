import base64
import datetime
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

CONFIG_PATH = "/opt/ranger-automation/bootstrap-config.json"
RANGER_URL = os.environ["RANGER_URL"].rstrip("/")
RANGER_PASSWORD = os.environ["RANGER_ADMIN_PASSWORD"]


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
        data = exc.read().decode("utf-8")
        if exc.code in ok:
            if not parse_json:
                return data
            return json.loads(data) if data else None
        exc.ranger_body = data
        print(f"Ranger API {method} {path} failed with HTTP {exc.code}: {data}")
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


def as_resource(value):
    if isinstance(value, dict):
        result = dict(value)
        result.setdefault("isExcludes", False)
        result.setdefault("isRecursive", False)
        if "values" in result and not isinstance(result["values"], list):
            result["values"] = [str(result["values"])]
        return result
    if value is None:
        values = ["*"]
    elif isinstance(value, list):
        values = [str(item) for item in value] or ["*"]
    else:
        values = [str(value)]
    return {"values": values, "isExcludes": False, "isRecursive": False}


def normalize_names(items):
    return sorted({str(item) for item in items if str(item).strip()})


def cleanup_config(config):
    return ((config.get("ranger") or {}).get("cleanup") or {})


def cleanup_enabled(config):
    cleanup = cleanup_config(config)
    return bool(cleanup.get("enabled", True))


def cleanup_dry_run(config):
    return bool(cleanup_config(config).get("dryRun", False))


def cleanup_names(config, legacy_key, cleanup_key):
    ranger_cfg = config.get("ranger") or {}
    names = normalize_names(ranger_cfg.get(legacy_key, []))
    if cleanup_enabled(config):
        names = normalize_names(names + normalize_names(cleanup_config(config).get(cleanup_key, [])))
    return names


def cleanup_user_matches_patterns(config, username):
    if not cleanup_enabled(config):
        return False
    username = str(username or "").strip()
    if not username:
        return False
    for pattern in normalize_names(cleanup_config(config).get("staleUserPatterns", [])):
        try:
            if re.search(pattern, username):
                return True
        except re.error as exc:
            print(f"WARNING: invalid Ranger cleanup staleUserPattern ignored: {pattern}: {exc}")
    return False


def cleanup_user_names(config):
    names = set(cleanup_names(config, "legacyManagedUsers", "staleUsers"))
    if cleanup_enabled(config):
        names.update(
            str(user.get("name", "")).strip()
            for user in list_users()
            if cleanup_user_matches_patterns(config, str(user.get("name", "")).strip())
        )
    return sorted(name for name in names if name)


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
        current = members.get(name)
        members[name] = role_member(name, is_admin or bool(current and current.get("isAdmin")))
    return [members[name] for name in sorted(members)]


def access_item(users, groups, roles, accesses):
    if not users and not groups and not roles:
        return None
    return {
        "users": normalize_names(users),
        "groups": normalize_names(groups),
        "roles": normalize_names(roles),
        "accesses": [{"type": access, "isAllowed": True} for access in accesses],
        "conditions": [],
        "delegateAdmin": False,
    }


def upsert_service(config):
    ranger_cfg = config["ranger"]
    service_name = ranger_cfg["serviceName"]
    payload = {
        "name": service_name,
        "type": "trino",
        "configs": {
            "username": ranger_cfg["serviceUsername"],
            "password": "",
            "jdbc.driverClassName": "io.trino.jdbc.TrinoDriver",
            "jdbc.url": config["trinoJdbcUrl"],
            "policy.download.auth.users": ranger_cfg["serviceUsername"],
            "tag.download.auth.users": ranger_cfg["serviceUsername"],
            "userstore.download.auth.users": ranger_cfg["serviceUsername"],
            "service.admin.users": ",".join(ranger_cfg.get("serviceAdminUsers", [])),
            "service.admin.groups": ",".join(ranger_cfg.get("serviceAdminGroups", [])),
            "ranger.plugin.super.users": ",".join(ranger_cfg.get("superUsers", [])),
            "ranger.plugin.super.groups": ",".join(ranger_cfg.get("superGroups", [])),
            "ranger.plugin.trino.policy.refresh.synchronous": "true",
        },
    }

    path = "/service/public/v2/api/service/name/" + urllib.parse.quote(service_name, safe="")
    try:
        existing = request("GET", path, ok=(200,))
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        existing = None

    if existing:
        payload["id"] = existing["id"]
        payload["guid"] = existing.get("guid")
        request("PUT", path, payload, ok=(200,))
    else:
        request("POST", "/service/public/v2/api/service/", payload, ok=(200, 201))


def normalize_policy(policy, service_name):
    normalized = dict(policy)
    normalized["service"] = service_name
    normalized["serviceType"] = "trino"
    normalized.setdefault("isEnabled", True)
    normalized.setdefault("isAuditEnabled", True)
    normalized.setdefault("policyType", 0)
    normalized["resources"] = {
        key: as_resource(value) for key, value in normalized.get("resources", {}).items()
    }
    normalized.setdefault("policyItems", [])
    normalized.setdefault("denyPolicyItems", [])
    normalized.setdefault("allowExceptions", [])
    normalized.setdefault("denyExceptions", [])
    normalized.setdefault("dataMaskPolicyItems", [])
    normalized.setdefault("rowFilterPolicyItems", [])
    return normalized


def role_update_path(role_id):
    return f"/service/public/v2/api/roles/{role_id}?createNonExistUserGroup=true"


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


def list_policies(service_name):
    path = "/service/public/v2/api/policy?serviceName=" + urllib.parse.quote(service_name, safe="")
    return request("GET", path, ok=(200,)) or []


def list_users():
    users = []
    start_index = 0
    page_size = 200
    while True:
        payload = request(
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


def list_groups():
    groups = []
    start_index = 0
    page_size = 200
    while True:
        payload = request(
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


def get_user(username):
    username = str(username or "").strip()
    if not username:
        return None
    for user in list_users():
        if str(user.get("name", "")).strip() == username:
            return user
    return None


def build_managed_user(username, first_name="", last_name="", email_address=""):
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
        "syncSource": "KEYCLOAK_LOCAL",
    }


def ensure_users_exist(usernames):
    existing_usernames = {
        str(user.get("name", "")).strip()
        for user in list_users()
        if str(user.get("name", "")).strip()
    }
    missing = [
        build_managed_user(username)
        for username in normalize_names(usernames)
        if username not in existing_usernames
    ]
    if not missing:
        return
    request(
        "POST",
        "/service/xusers/ugsync/users",
        {"vXUsers": missing},
        ok=(200, 201),
    )
    print("Seeded Ranger users: " + ", ".join(sorted(user["name"] for user in missing)))


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


def policy_path(policy_id):
    return "/service/public/v2/api/policy/" + urllib.parse.quote(str(policy_id), safe="")


def filter_role_from_policy_items(items, role_name):
    filtered_items = []
    removed = False
    for item in items or []:
        updated_item = dict(item)
        roles = normalize_names(name for name in item.get("roles", []) if str(name) != role_name)
        removed = removed or len(roles) != len(item.get("roles", []) or [])
        updated_item["roles"] = roles
        updated_item["users"] = normalize_names(item.get("users", []))
        updated_item["groups"] = normalize_names(item.get("groups", []))
        if updated_item["users"] or updated_item["groups"] or updated_item["roles"]:
            filtered_items.append(updated_item)
    return filtered_items, removed


def detach_role_from_policies(service_name, role_name):
    for policy in list_policies(service_name):
        updated_policy = dict(policy)
        removed = False
        for key in [
            "policyItems",
            "denyPolicyItems",
            "allowExceptions",
            "denyExceptions",
            "dataMaskPolicyItems",
            "rowFilterPolicyItems",
        ]:
            filtered_items, key_removed = filter_role_from_policy_items(policy.get(key, []), role_name)
            updated_policy[key] = filtered_items
            removed = removed or key_removed

        if not removed:
            continue

        has_principals = any(
            updated_policy.get(key)
            for key in [
                "policyItems",
                "denyPolicyItems",
                "allowExceptions",
                "denyExceptions",
                "dataMaskPolicyItems",
                "rowFilterPolicyItems",
            ]
        )
        if has_principals:
            request("PUT", policy_path(policy["id"]), updated_policy, ok=(200,))
            print(f"Detached legacy role {role_name} from Ranger policy: {policy['name']}")
        else:
            request("DELETE", policy_path(policy["id"]), ok=(204, 404))
            print(f"Deleted stale Ranger policy with no remaining principals: {policy['name']}")


def build_catalog_acl_policies(config):
    service_name = config["ranger"]["serviceName"]
    read_accesses = ["select", "show", "use", "execute"]
    write_accesses = read_accesses + ["insert", "create", "delete", "drop", "alter", "grant", "revoke"]
    policies = []

    if not config["ranger"].get("importCatalogAcls", False):
        return policies

    for catalog_name, catalog in config.get("catalogs", {}).items():
        roles_acl = catalog.get("authorizedRoles", {}) or {}
        users_acl = catalog.get("authorizedUsers", {}) or {}
        read_item = access_item(users_acl.get("read", []), [], roles_acl.get("read", []), read_accesses)
        write_item = access_item(users_acl.get("write", []), [], roles_acl.get("write", []), write_accesses)
        policy_items = [item for item in [read_item, write_item] if item]

        if policy_items:
            policies.append(
                normalize_policy(
                    {
                        "name": f"{service_name}-{catalog_name}-access",
                        "description": f"Imported catalog access policy for {catalog_name}.",
                        "resources": {
                            "catalog": catalog_name,
                            "schema": "*",
                            "table": "*",
                            "column": "*",
                        },
                        "policyItems": policy_items,
                    },
                    service_name,
                )
            )

    return policies


def policy_resource_values(policy, resource_key):
    resource = (policy.get("resources") or {}).get(resource_key)
    if resource is None:
        return []
    if isinstance(resource, dict):
        values = resource.get("values", resource.get("value", []))
        if isinstance(values, list):
            return normalize_names(values)
        return normalize_names([values])
    if isinstance(resource, list):
        return normalize_names(resource)
    return normalize_names([resource])


def policy_has_resource(policy, resource_key):
    return resource_key in (policy.get("resources") or {})


def has_self_trinouser_policy(policies):
    for policy in policies or []:
        values = policy_resource_values(policy, "trinouser")
        if "{USER}" in values:
            return True
    return False


def build_trino_baseline_policies(config):
    service_name = config["ranger"]["serviceName"]
    if not config["ranger"].get("trinoEnabled", False):
        return []
    bootstrap_policies = config["ranger"].get("bootstrapPolicies", []) or []
    has_explicit_queryid_policy = any(
        policy_has_resource(policy, "queryid") for policy in bootstrap_policies
    )
    has_explicit_self_trinouser_policy = has_self_trinouser_policy(bootstrap_policies)
    has_explicit_system_policy = any(
        str((policy.get("resources") or {}).get("catalog")) == "system"
        for policy in bootstrap_policies
    )
    policies = []
    if not has_explicit_queryid_policy:
        policies.append(
            normalize_policy(
                {
                    "name": "all - queryid",
                    "description": "Required Trino/Ranger baseline policy that lets each authenticated user execute their own queries.",
                    "resources": {
                        "queryid": "*",
                    },
                    "policyItems": [
                        {
                            "users": [],
                            "groups": ["public"],
                            "roles": [],
                            "accesses": [
                                {"type": "execute", "isAllowed": True},
                            ],
                            "conditions": [],
                            "delegateAdmin": False,
                        },
                    ],
                },
                service_name,
            )
        )
    if not has_explicit_self_trinouser_policy:
        policies.append(
            normalize_policy(
                {
                    "name": "all - trinouser",
                    "description": "Required Trino/Ranger baseline policy that lets each authenticated principal become the matching Trino user.",
                    "resources": {
                        "trinouser": "{USER}",
                    },
                    "policyItems": [
                        {
                            "users": [],
                            "groups": ["public"],
                            "roles": [],
                            "accesses": [
                                {"type": "impersonate", "isAllowed": True},
                            ],
                            "conditions": [],
                            "delegateAdmin": False,
                        },
                    ],
                },
                service_name,
            )
        )
    if not has_explicit_system_policy:
        policies.append(
            normalize_policy(
                {
                    "name": "all - system",
                    "description": "Allow each authenticated user to read JDBC metadata in the system catalog.",
                    "resources": {
                        "catalog": "system",
                        "schema": "jdbc",
                        "table": "*",
                        "column": "*",
                    },
                    "policyItems": [
                        {
                            "users": [],
                            "groups": ["public"],
                            "roles": [],
                            "accesses": [
                                {"type": "select", "isAllowed": True},
                                {"type": "show", "isAllowed": True},
                                {"type": "use", "isAllowed": True},
                            ],
                            "conditions": [],
                            "delegateAdmin": False,
                        },
                    ],
                },
                service_name,
            )
        )
    return policies


def usernames_from_policy_items(items):
    usernames = set()
    for item in items or []:
        usernames.update(normalize_names(item.get("users", [])))
    return usernames


def policy_principal_usernames(config, policies):
    usernames = set()
    ranger_cfg = config.get("ranger", {}) or {}
    usernames.update(normalize_names(ranger_cfg.get("serviceAdminUsers", [])))
    usernames.update(normalize_names(ranger_cfg.get("superUsers", [])))
    service_username = str(ranger_cfg.get("serviceUsername") or "").strip()
    if service_username:
        usernames.add(service_username)
    for policy in policies or []:
        for key in [
            "policyItems",
            "denyPolicyItems",
            "allowExceptions",
            "denyExceptions",
            "dataMaskPolicyItems",
            "rowFilterPolicyItems",
        ]:
            usernames.update(usernames_from_policy_items(policy.get(key, [])))
    return usernames


def purge_legacy_roles(config, service_name):
    existing_roles_by_name = {
        str(role.get("name", "")): role
        for role in list_roles()
        if str(role.get("name", "")).strip()
    }
    for stale_role_name in cleanup_names(config, "legacyManagedRoles", "staleRoles"):
        if stale_role_name in existing_roles_by_name:
            if cleanup_dry_run(config):
                print(f"DRY RUN: would delete stale managed Ranger role: {stale_role_name}")
                continue
            detach_role_from_policies(service_name, stale_role_name)
            delete_role(service_name, stale_role_name)
            print(f"Deleted stale managed Ranger role: {stale_role_name}")


def filter_user_from_role_members(items, username):
    filtered = []
    removed = False
    for item in items or []:
        name = str(item.get("name", "")).strip() if isinstance(item, dict) else str(item).strip()
        if name == username:
            removed = True
            continue
        filtered.append(item)
    return filtered, removed


def detach_user_from_roles(service_name, username):
    for role in list_roles():
        filtered_users, removed = filter_user_from_role_members(role.get("users", []), username)
        if not removed:
            continue
        payload = {
            "id": role["id"],
            "guid": role.get("guid"),
            "version": role.get("version"),
            "createdByUser": role.get("createdByUser"),
            "name": role["name"],
            "description": role.get("description", ""),
            "isEnabled": bool(role.get("isEnabled", True)),
            "users": normalize_role_members(filtered_users),
            "groups": normalize_role_members(role.get("groups", [])),
            "roles": normalize_role_members(role.get("roles", [])),
        }
        request("PUT", role_update_path(role["id"]), payload, ok=(200,))
        print(f"Detached legacy user {username} from Ranger role: {role['name']}")


def filter_user_from_policy_items(items, username):
    filtered_items = []
    removed = False
    for item in items or []:
        updated_item = dict(item)
        users = normalize_names(name for name in item.get("users", []) if str(name) != username)
        removed = removed or len(users) != len(item.get("users", []) or [])
        updated_item["users"] = users
        updated_item["groups"] = normalize_names(item.get("groups", []))
        updated_item["roles"] = normalize_names(item.get("roles", []))
        if updated_item["users"] or updated_item["groups"] or updated_item["roles"]:
            filtered_items.append(updated_item)
    return filtered_items, removed


def detach_user_from_policies(service_name, username):
    for policy in list_policies(service_name):
        updated_policy = dict(policy)
        removed = False
        for key in [
            "policyItems",
            "denyPolicyItems",
            "allowExceptions",
            "denyExceptions",
            "dataMaskPolicyItems",
            "rowFilterPolicyItems",
        ]:
            filtered_items, key_removed = filter_user_from_policy_items(policy.get(key, []), username)
            updated_policy[key] = filtered_items
            removed = removed or key_removed

        if not removed:
            continue

        has_principals = any(
            updated_policy.get(key)
            for key in [
                "policyItems",
                "denyPolicyItems",
                "allowExceptions",
                "denyExceptions",
                "dataMaskPolicyItems",
                "rowFilterPolicyItems",
            ]
        )
        if has_principals:
            request("PUT", policy_path(policy["id"]), updated_policy, ok=(200,))
            print(f"Detached legacy user {username} from Ranger policy: {policy['name']}")
        else:
            request("DELETE", policy_path(policy["id"]), ok=(204, 404))
            print(f"Deleted stale Ranger policy with no remaining principals: {policy['name']}")


def delete_user_by_name(username):
    user = get_user(username)
    if not user:
        return
    request(
        "DELETE",
        f"/service/xusers/secure/users/id/{user['id']}?forceDelete=true",
        ok=(200, 204, 404),
        parse_json=False,
    )
    print(f"Deleted stale Ranger user: {username}")


def purge_legacy_users(config, service_name, protected_usernames=None):
    protected_usernames = set(normalize_names(protected_usernames or []))
    for username in cleanup_user_names(config):
        if username in protected_usernames:
            print(f"Skipping stale Ranger user cleanup because it is still desired: {username}")
            continue
        if cleanup_dry_run(config):
            print(f"DRY RUN: would delete stale Ranger user: {username}")
            continue
        detach_user_from_roles(service_name, username)
        detach_user_from_policies(service_name, username)
        delete_user_by_name(username)


def delete_group_by_name(group_name):
    existing = None
    for group in list_groups():
        name = str(group.get("name", "")).strip()
        if name == group_name:
            existing = group
            break
    if not existing:
        return
    request(
        "DELETE",
        f"/service/xusers/groups/{existing['id']}",
        ok=(200, 204, 404),
        parse_json=False,
    )
    print(f"Deleted stale Ranger group: {group_name}")


def purge_legacy_groups(config):
    for group_name in cleanup_names(config, "legacyManagedGroups", "staleGroups"):
        if cleanup_dry_run(config):
            print(f"DRY RUN: would delete stale Ranger group: {group_name}")
            continue
        delete_group_by_name(group_name)


def delete_policy_by_name(service_name, policy_name):
    path = (
        "/service/public/v2/api/service/"
        + urllib.parse.quote(service_name, safe="")
        + "/policy/"
        + urllib.parse.quote(policy_name, safe="")
    )
    try:
        existing = request("GET", path, ok=(200,))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return
        raise
    request("DELETE", policy_path(existing["id"]), ok=(200, 204, 404))
    print(f"Deleted stale Ranger policy: {policy_name}")


def purge_legacy_policies(config, service_name):
    for policy_name in cleanup_names(config, "legacyManagedPolicies", "stalePolicies"):
        if cleanup_dry_run(config):
            print(f"DRY RUN: would delete stale Ranger policy: {policy_name}")
            continue
        delete_policy_by_name(service_name, policy_name)


def normalize_policy_resource(value):
    normalized = as_resource(value)
    normalized["values"] = sorted(str(item) for item in normalized.get("values", []))
    normalized["isExcludes"] = bool(normalized.get("isExcludes", False))
    normalized["isRecursive"] = bool(normalized.get("isRecursive", False))
    return normalized


def upsert_policy(service_name, policy):
    name = policy["name"]
    path = (
        "/service/public/v2/api/service/"
        + urllib.parse.quote(service_name, safe="")
        + "/policy/"
        + urllib.parse.quote(name, safe="")
    )
    try:
        existing = request("GET", path, ok=(200,))
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        existing = None

    if existing:
        policy["id"] = existing["id"]
        policy["guid"] = existing.get("guid")
        request("PUT", path, policy, ok=(200,))
    else:
        try:
            request("POST", "/service/public/v2/api/policy/", policy, ok=(200, 201))
        except urllib.error.HTTPError as exc:
            if exc.code != 400:
                raise
            detail = getattr(exc, "ranger_body", "")
            match = re.search(r"policy-name=\[([^\]]+)\]", detail)
            if not match:
                raise
            existing_name = match.group(1).strip()
            existing_path = (
                "/service/public/v2/api/service/"
                + urllib.parse.quote(service_name, safe="")
                + "/policy/"
                + urllib.parse.quote(existing_name, safe="")
            )
            existing = request("GET", existing_path, ok=(200,))
            if not existing:
                raise
            policy["id"] = existing["id"]
            policy["guid"] = existing.get("guid")
            update_path = (
                "/service/public/v2/api/policy/"
                + urllib.parse.quote(str(existing["id"]), safe="")
            )
            request("PUT", update_path, policy, ok=(200,))


def main():
    wait_for_ranger()
    config = load_config()
    service_name = config["ranger"]["serviceName"]
    upsert_service(config)
    purge_legacy_roles(config, service_name)

    policies = []
    policies.extend(build_trino_baseline_policies(config))
    policies.extend(build_catalog_acl_policies(config))
    for raw_policy in config["ranger"].get("bootstrapPolicies", []):
        policies.append(normalize_policy(raw_policy, service_name))

    desired_policy_usernames = policy_principal_usernames(config, policies)
    ensure_users_exist(desired_policy_usernames)
    purge_legacy_users(config, service_name, desired_policy_usernames)
    purge_legacy_groups(config)
    purge_legacy_policies(config, service_name)

    for policy in policies:
        upsert_policy(service_name, policy)
        print(f"Reconciled Ranger policy: {policy['name']}")


if __name__ == "__main__":
    main()
