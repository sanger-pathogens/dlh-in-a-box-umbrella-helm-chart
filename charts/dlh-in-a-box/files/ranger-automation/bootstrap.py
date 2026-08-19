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


def role_create_path():
    return "/service/public/v2/api/roles?createNonExistUserGroup=true"


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


def upsert_role(role):
    payload = {
        "name": role["name"],
        "description": role.get("description", ""),
        "isEnabled": bool(role.get("isEnabled", True)),
        "users": normalize_role_members(role.get("users", [])),
        "groups": normalize_role_members(role.get("groups", [])),
        "roles": normalize_role_members(role.get("roles", [])),
    }
    existing = get_role(None, role["name"])
    if existing:
        payload["id"] = existing["id"]
        payload["guid"] = existing.get("guid")
        payload["version"] = existing.get("version")
        payload["createdByUser"] = existing.get("createdByUser")
        request("PUT", role_update_path(existing["id"]), payload, ok=(200,))
    else:
        request("POST", role_create_path(), payload, ok=(200, 201))


def reconcile_data_roles(config, service_name):
    data_roles = (config.get("ranger") or {}).get("dataRoles") or {}
    desired_role_names = set()
    for role_name in sorted(data_roles):
        role_config = data_roles.get(role_name) or {}
        if not isinstance(role_config, dict) or role_config.get("enabled") is False:
            continue
        desired_role_names.add(role_name)
        existing = get_role(None, role_name)
        upsert_role(
            {
                "name": role_name,
                "description": role_config.get("description")
                or f"Data access role managed by Ranger bootstrap: {role_name}.",
                "isEnabled": True,
                "users": (existing or {}).get("users", []),
                "groups": (existing or {}).get("groups", []),
                "roles": (existing or {}).get("roles", []),
            }
        )
        print(f"Reconciled Ranger data role: {role_name}")

    for role in list_roles():
        role_name = str(role.get("name", "")).strip()
        if not role_name or role_name in desired_role_names:
            continue
        detach_role_from_policies(service_name, role_name)
        delete_role(service_name, role_name)
        print(f"Deleted Ranger role not declared in dataRoles: {role_name}")


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

    for catalog_name, catalog in config.get("catalogs", {}).items():
        roles_acl = catalog.get("authorizedRoles", {}) or {}
        read_item = access_item([], [], roles_acl.get("read", []), read_accesses)
        write_item = access_item([], [], roles_acl.get("write", []), write_accesses)
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


BASELINE_TRINO_POLICIES = {
    "selfQueryExecution": {
        "name": "all - queryid",
        "description": "Lets each authenticated user execute their own queries.",
        "resources": {"queryid": "*"},
        "accesses": ["execute"],
    },
    "selfImpersonation": {
        "name": "all - trinouser",
        "description": "Lets each authenticated principal become the matching Trino user.",
        "resources": {"trinouser": "{USER}"},
        "accesses": ["impersonate"],
    },
    "systemCatalogMetadata": {
        "name": "all - system",
        "description": "Allows each authenticated user to read JDBC metadata in the system catalog.",
        "resources": {"catalog": "system", "schema": "jdbc", "table": "*", "column": "*"},
        "accesses": ["select", "show", "use"],
    },
}


def build_trino_baseline_policies(config):
    service_name = config["ranger"]["serviceName"]
    if not config["ranger"].get("trinoEnabled", False):
        return [], []

    toggles = config["ranger"].get("baselinePolicies") or {}
    policies = []
    removed_names = []
    for key, defaults in BASELINE_TRINO_POLICIES.items():
        toggle = toggles.get(key) or {}
        name = str(toggle.get("name") or defaults["name"])
        if toggle.get("enabled", True):
            policies.append(
                normalize_policy(
                    {
                        "name": name,
                        "description": str(toggle.get("description") or defaults["description"]),
                        "resources": defaults["resources"],
                        "policyItems": [
                            {
                                "users": [],
                                "groups": [],
                                "roles": [],
                                "accesses": [
                                    {"type": access, "isAllowed": True}
                                    for access in defaults["accesses"]
                                ],
                                "conditions": [],
                                "delegateAdmin": False,
                            },
                        ],
                    },
                    service_name,
                )
            )
        else:
            removed_names.append(name)
    return policies, removed_names


def delete_policy_by_name(service_name, name):
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
        return
    if existing:
        request("DELETE", policy_path(existing["id"]), ok=(204, 404))


def normalize_policy_resource(value):
    normalized = as_resource(value)
    normalized["values"] = sorted(str(item) for item in normalized.get("values", []))
    normalized["isExcludes"] = bool(normalized.get("isExcludes", False))
    normalized["isRecursive"] = bool(normalized.get("isRecursive", False))
    return normalized


def policy_item_compare_key(item):
    normalized = json.loads(json.dumps(item or {}))
    for key in ["users", "groups", "roles"]:
        if key in normalized:
            normalized[key] = normalize_names(normalized.get(key, []))
    if "accesses" in normalized:
        normalized["accesses"] = sorted(
            normalized.get("accesses", []),
            key=lambda value: json.dumps(value, sort_keys=True),
        )
    return json.dumps(normalized, sort_keys=True)


def merge_policy_item_list(existing_items, desired_items):
    merged = list(existing_items or [])
    seen = {policy_item_compare_key(item) for item in merged}
    for item in desired_items or []:
        key = policy_item_compare_key(item)
        if key not in seen:
            merged.append(item)
            seen.add(key)
    return merged


def merge_policy_items(existing, desired):
    merged = dict(existing)
    for key in [
        "policyItems",
        "denyPolicyItems",
        "allowExceptions",
        "denyExceptions",
        "dataMaskPolicyItems",
        "rowFilterPolicyItems",
    ]:
        merged[key] = merge_policy_item_list(existing.get(key, []), desired.get(key, []))
    return merged


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
            update_path = (
                "/service/public/v2/api/policy/"
                + urllib.parse.quote(str(existing["id"]), safe="")
            )
            if existing_name == name:
                policy["id"] = existing["id"]
                policy["guid"] = existing.get("guid")
                request("PUT", update_path, policy, ok=(200,))
            else:
                request("PUT", update_path, merge_policy_items(existing, policy), ok=(200,))
                print(
                    "Merged Ranger policy "
                    + repr(name)
                    + " into existing colliding policy "
                    + repr(existing_name)
                )


def main():
    wait_for_ranger()
    config = load_config()
    service_name = config["ranger"]["serviceName"]
    upsert_service(config)
    reconcile_data_roles(config, service_name)

    baseline_policies, disabled_baseline_policy_names = build_trino_baseline_policies(config)
    policies = []
    policies.extend(baseline_policies)
    policies.extend(build_catalog_acl_policies(config))

    for policy in policies:
        upsert_policy(service_name, policy)
        print(f"Reconciled Ranger policy: {policy['name']}")

    for name in disabled_baseline_policy_names:
        delete_policy_by_name(service_name, name)
        print(f"Removed disabled Ranger baseline policy: {name}")


if __name__ == "__main__":
    main()
