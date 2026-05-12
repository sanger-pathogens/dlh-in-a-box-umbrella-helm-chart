#!/usr/bin/env python3
"""Validate the DLH-in-a-box IcePanel JSON model.

This validator intentionally avoids third-party dependencies. It supports the
JSON Schema features used by dlh-in-a-box.schema.json and adds a semantic pass
for model references that JSON Schema alone does not express.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse
from typing import Any


DEFAULT_MODEL = Path("docs/architecture/icepanel/models/dlh-in-a-box.json")
DEFAULT_SCHEMA = Path("docs/architecture/icepanel/models/dlh-in-a-box.schema.json")
GITHUB_REPO_URL = "https://github.com/sanger-pathogens/dlh-in-a-box-umbrella-helm-chart"
KNOWN_TAG_IDS = {
    "PpEgyQQaEuEyVUQB4LjJ",  # Wellcome Sanger Institute
    "S193ciAwZE82mjfqMqis",  # Cloud
    "WO7YSm1hYmsluPUMBazn",  # icddr,b
}
KNOWN_TEAM_IDS = {
    "3oUnOCRreilVIoZlTSY1",  # Sanger PaM Informatics
    "7AGfmNPSUb6reqBrX3Gk",  # icddr,b Scientists
    "WdIHvpTJvsRa639Od2vX",  # Sanger IDS (ISG)
    "YD4KdnnwJtWane4R039f",  # Sanger PaM Data Engineering and Integration
    "yNlfFPPI683RFZ2aq3bk",  # icddr,b IT
}
RUNTIME_GROUP_BY_OBJECT = {
    "DLH-R-PLATFORM-HOME": "DLH-G-runtime-BROWSER-ENTRY",
    "DLH-R-AUTH-PROXIES": "DLH-G-runtime-BROWSER-ENTRY",
    "DLH-R-KEYCLOAK": "DLH-G-runtime-IDENTITY-AND-SECRETS",
    "DLH-R-VAULT": "DLH-G-runtime-IDENTITY-AND-SECRETS",
    "DLH-R-RANGER": "DLH-G-runtime-GOVERNANCE",
    "DLH-R-TRINO": "DLH-G-runtime-LAKEHOUSE-CORE",
    "DLH-R-HIVE": "DLH-G-runtime-LAKEHOUSE-CORE",
    "DLH-R-MINIO": "DLH-G-runtime-LAKEHOUSE-CORE",
    "DLH-R-SUPERSET": "DLH-G-runtime-ANALYSIS-TOOLS",
    "DLH-R-JUPYTERHUB": "DLH-G-runtime-ANALYSIS-TOOLS",
    "DLH-R-JUPYTER-PODS": "DLH-G-runtime-ANALYSIS-TOOLS",
    "DLH-R-CLOUDBEAVER": "DLH-G-runtime-ANALYSIS-TOOLS",
    "DLH-R-PREFECT-SERVER": "DLH-G-runtime-ORCHESTRATION-AND-COMPUTE",
    "DLH-R-PREFECT-WORKER": "DLH-G-runtime-ORCHESTRATION-AND-COMPUTE",
    "DLH-R-SPARK-OPERATOR": "DLH-G-runtime-ORCHESTRATION-AND-COMPUTE",
    "DLH-R-DATAHUB": "DLH-G-runtime-DISCOVERY",
    "DLH-R-KEYCLOAK-DB": "DLH-G-runtime-SUPPORT-SERVICES-AND-STORES",
    "DLH-R-RANGER-DB": "DLH-G-runtime-SUPPORT-SERVICES-AND-STORES",
    "DLH-R-HIVE-DB": "DLH-G-runtime-SUPPORT-SERVICES-AND-STORES",
    "DLH-R-SUPERSET-DB": "DLH-G-runtime-SUPPORT-SERVICES-AND-STORES",
    "DLH-R-SUPERSET-REDIS": "DLH-G-runtime-SUPPORT-SERVICES-AND-STORES",
    "DLH-R-PREFECT-DB": "DLH-G-runtime-SUPPORT-SERVICES-AND-STORES",
    "DLH-R-DATAHUB-MYSQL": "DLH-G-runtime-SUPPORT-SERVICES-AND-STORES",
    "DLH-R-DATAHUB-KAFKA": "DLH-G-runtime-SUPPORT-SERVICES-AND-STORES",
    "DLH-R-DATAHUB-ELASTICSEARCH": "DLH-G-runtime-SUPPORT-SERVICES-AND-STORES",
}
RUNTIME_GROUP_IDS = set(RUNTIME_GROUP_BY_OBJECT.values())
SUPPORT_GROUP_ID = "DLH-G-runtime-SUPPORT-SERVICES-AND-STORES"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def resolve_ref(schema: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError(f"Only local JSON Schema references are supported: {ref}")
    node: Any = schema
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def validate_schema_node(
    value: Any,
    node: dict[str, Any],
    root_schema: dict[str, Any],
    path: str,
    errors: list[str],
) -> None:
    if "$ref" in node:
        validate_schema_node(value, resolve_ref(root_schema, node["$ref"]), root_schema, path, errors)
        return

    if "oneOf" in node:
        before_counts = []
        for option in node["oneOf"]:
            option_errors: list[str] = []
            validate_schema_node(value, option, root_schema, path, option_errors)
            before_counts.append(len(option_errors))
        if sum(count == 0 for count in before_counts) != 1:
            errors.append(f"{path}: value must match exactly one allowed schema")
        return

    if "const" in node and value != node["const"]:
        errors.append(f"{path}: expected constant {node['const']!r}")

    if "enum" in node and value not in node["enum"]:
        errors.append(f"{path}: expected one of {node['enum']!r}")

    expected_type = node.get("type")
    if expected_type and not type_matches(value, expected_type):
        errors.append(f"{path}: expected {expected_type}, got {type(value).__name__}")
        return

    if isinstance(value, str):
        if len(value) < node.get("minLength", 0):
            errors.append(f"{path}: string is shorter than minLength")
        if "pattern" in node and not re.search(node["pattern"], value):
            errors.append(f"{path}: does not match pattern {node['pattern']!r}")

    if isinstance(value, int) and not isinstance(value, bool):
        if "minimum" in node and value < node["minimum"]:
            errors.append(f"{path}: value is below minimum {node['minimum']}")

    if isinstance(value, list):
        if len(value) < node.get("minItems", 0):
            errors.append(f"{path}: array is shorter than minItems")
        if "items" in node:
            for index, item in enumerate(value):
                validate_schema_node(item, node["items"], root_schema, f"{path}[{index}]", errors)

    if isinstance(value, dict):
        required = node.get("required") or []
        for key in required:
            if key not in value:
                errors.append(f"{path}: missing required property {key!r}")
        properties = node.get("properties") or {}
        additional = node.get("additionalProperties", True)
        for key, item in value.items():
            if key in properties:
                validate_schema_node(item, properties[key], root_schema, f"{path}.{key}", errors)
            elif isinstance(additional, dict):
                validate_schema_node(item, additional, root_schema, f"{path}.{key}", errors)
            elif additional is False:
                errors.append(f"{path}: unexpected property {key!r}")


def validate_semantics(model: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    object_ids = [item["id"] for item in model["objects"]]
    connection_ids = [item["id"] for item in model["connections"]]
    diagram_keys = [item["key"] for item in model["diagrams"]]
    export_filenames = [item["exportFilename"] for item in model["diagrams"]]
    object_by_id = {item["id"]: item for item in model["objects"]}
    connection_by_id = {item["id"]: item for item in model["connections"]}

    for label, values in [
        ("object id", object_ids),
        ("connection id", connection_ids),
        ("diagram key", diagram_keys),
        ("export filename", export_filenames),
    ]:
        duplicates = sorted({value for value in values if values.count(value) > 1})
        for value in duplicates:
            errors.append(f"duplicate {label}: {value}")

    object_id_set = set(object_ids)
    connection_id_set = set(connection_ids)

    for item in model["objects"]:
        caption = item.get("caption", "")
        if caption and len(caption) > 240:
            errors.append(f"object {item['id']} caption is too long for an IcePanel card")
        for label_key, label_value in (item.get("labels") or {}).items():
            if "`" in str(label_value):
                errors.append(
                    f"object {item['id']} label {label_key!r} contains Markdown backticks"
                )
        for field, known_ids in [("tagIds", KNOWN_TAG_IDS), ("teamIds", KNOWN_TEAM_IDS)]:
            values = item.get(field) or []
            duplicates = sorted({value for value in values if values.count(value) > 1})
            for value in duplicates:
                errors.append(f"object {item['id']} has duplicate {field} value: {value}")
            for value in values:
                if value not in known_ids:
                    errors.append(f"object {item['id']} has unknown {field} value: {value}")
        parent = item.get("parent")
        if parent is not None and parent not in object_id_set:
            errors.append(f"object {item['id']} parent does not exist: {parent}")
        for group_id in item.get("groups") or []:
            if group_id not in object_id_set:
                errors.append(f"object {item['id']} group does not exist: {group_id}")
                continue
            group = object_by_id[group_id]
            if group["type"] != "group":
                errors.append(f"object {item['id']} group is not a group object: {group_id}")
            if item["type"] == "group":
                errors.append(f"group object {item['id']} must not be assigned to group {group_id}")
        seen_link_urls: set[str] = set()
        for link in item.get("links") or []:
            url = link["url"]
            if url in seen_link_urls:
                errors.append(f"object {item['id']} has duplicate link URL: {url}")
            seen_link_urls.add(url)
            if not url.startswith("https://github.com/"):
                errors.append(f"object {item['id']} link is not a GitHub URL: {url}")
            if "/main" not in url:
                errors.append(f"object {item['id']} link does not target main branch: {url}")
            local_path = github_main_path(url)
            if local_path is not None and local_path != "":
                target = Path(local_path)
                if not target.exists():
                    errors.append(f"object {item['id']} link target does not exist locally: {local_path}")

    for item in model["connections"]:
        if item["origin"] not in object_id_set:
            errors.append(f"connection {item['id']} origin does not exist: {item['origin']}")
        elif object_by_id[item["origin"]]["type"] == "group":
            errors.append(f"connection {item['id']} origin must not be a group: {item['origin']}")
        if item["target"] not in object_id_set:
            errors.append(f"connection {item['id']} target does not exist: {item['target']}")
        elif object_by_id[item["target"]]["type"] == "group":
            errors.append(f"connection {item['id']} target must not be a group: {item['target']}")

    for item in model["diagrams"]:
        model_object = item.get("modelObject")
        if model_object is not None and model_object not in object_id_set:
            errors.append(f"diagram {item['key']} modelObject does not exist: {model_object}")
        diagram_object_ids = set(item["objects"])
        for object_id in item["objects"]:
            if object_id not in object_id_set:
                errors.append(f"diagram {item['key']} object does not exist: {object_id}")
        for connection_id in item["connections"]:
            if connection_id not in connection_id_set:
                errors.append(f"diagram {item['key']} connection does not exist: {connection_id}")
                continue
            connection = connection_by_id[connection_id]
            if connection["origin"] not in diagram_object_ids:
                errors.append(
                    f"diagram {item['key']} connection {connection_id} origin is not shown: {connection['origin']}"
                )
            if connection["target"] not in diagram_object_ids:
                errors.append(
                    f"diagram {item['key']} connection {connection_id} target is not shown: {connection['target']}"
                )
        errors.extend(validate_parent_area(item, object_by_id))
        errors.extend(validate_diagram_connectivity(item, object_by_id, connection_by_id))
        errors.extend(validate_diagram_groups(item, object_by_id))
        errors.extend(validate_diagram_geometry(item, object_by_id, connection_by_id))

    errors.extend(validate_runtime_groups(model, object_by_id))

    if len(model["diagrams"]) != 11:
        errors.append(f"expected 11 official diagrams, found {len(model['diagrams'])}")

    return errors


def validate_diagram_geometry(
    diagram: dict[str, Any],
    object_by_id: dict[str, dict[str, Any]],
    connection_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    diagram_key = diagram["key"]
    boxes: dict[str, dict[str, int]] = {}
    for index, object_id in enumerate(diagram["objects"]):
        obj = object_by_id.get(object_id)
        if not obj:
            continue
        layout = (obj.get("layout") or {}).get(diagram_key)
        if layout:
            boxes[object_id] = layout
        else:
            boxes[object_id] = {
                "x": 80 + (index % 4) * 360,
                "y": 80 + (index // 4) * 190,
                "width": 256,
                "height": 128,
            }

    non_group_ids = [
        object_id
        for object_id in diagram["objects"]
        if object_by_id.get(object_id, {}).get("type") != "group"
    ]
    for index, first_id in enumerate(non_group_ids):
        for second_id in non_group_ids[index + 1 :]:
            if box_intersects_with_padding(boxes[first_id], boxes[second_id], padding=8):
                errors.append(
                    f"diagram {diagram_key} objects overlap: {first_id} and {second_id}"
                )

    for connection_id in diagram["connections"]:
        connection = connection_by_id.get(connection_id)
        if not connection:
            continue
        origin = connection["origin"]
        target = connection["target"]
        if origin not in boxes or target not in boxes:
            continue
        points = connection_points_for_diagram(diagram_key, connection, boxes[origin], boxes[target])
        for object_id in non_group_ids:
            if object_id in {origin, target}:
                continue
            if polyline_intersects_box(points, boxes[object_id], padding=8):
                errors.append(
                    f"diagram {diagram_key} connection {connection_id} crosses object {object_id}"
                )
                break
    return errors


def validate_diagram_connectivity(
    diagram: dict[str, Any],
    object_by_id: dict[str, dict[str, Any]],
    connection_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    diagram_object_ids = set(diagram["objects"])
    degree = {object_id: 0 for object_id in diagram_object_ids}
    for connection_id in diagram["connections"]:
        connection = connection_by_id.get(connection_id)
        if not connection:
            continue
        for endpoint_key in ("origin", "target"):
            endpoint = connection[endpoint_key]
            if endpoint in degree:
                degree[endpoint] += 1

    for object_id, count in sorted(degree.items()):
        obj = object_by_id.get(object_id)
        if obj and obj["type"] != "group" and count == 0:
            errors.append(f"diagram {diagram['key']} object {object_id} has no visible connection")
    return errors


def validate_diagram_groups(
    diagram: dict[str, Any],
    object_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    diagram_key = diagram["key"]
    diagram_object_ids = set(diagram["objects"])
    group_ids = sorted(
        object_id
        for object_id in diagram_object_ids
        if object_by_id.get(object_id, {}).get("type") == "group"
    )

    for group_id in group_ids:
        group = object_by_id[group_id]
        members = sorted(
            object_id
            for object_id in diagram_object_ids
            if group_id in (object_by_id.get(object_id, {}).get("groups") or [])
        )
        if not members:
            errors.append(f"diagram {diagram_key} group {group_id} has no visible member objects")
            continue

        group_layout = (group.get("layout") or {}).get(diagram_key)
        if not group_layout:
            continue
        for member_id in members:
            member_layout = (object_by_id[member_id].get("layout") or {}).get(diagram_key)
            if not member_layout:
                errors.append(
                    f"diagram {diagram_key} grouped object {member_id} has no layout for group {group_id}"
                )
            elif not box_contains(group_layout, member_layout):
                errors.append(
                    f"diagram {diagram_key} grouped object {member_id} is outside group {group_id}"
                )
    return errors


def print_link_audit(model: dict[str, Any]) -> None:
    linked = 0
    unlinked = []
    for item in model["objects"]:
        if item.get("links"):
            linked += 1
        else:
            unlinked.append(f"{item['id']} | {item['name']} | {item['type']}")
    print(f"Reality link audit: {linked} linked, {len(unlinked)} intentionally unlinked or pending")
    for line in unlinked:
        print(f"- {line}")


def validate_parent_area(
    diagram: dict[str, Any],
    object_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    parent_area = diagram.get("parentAreaBounds")
    model_object = diagram.get("modelObject")
    if not parent_area or not model_object:
        return errors

    for object_id in diagram["objects"]:
        obj = object_by_id.get(object_id)
        if not obj:
            continue
        layout = (obj.get("layout") or {}).get(diagram["key"])
        if not layout:
            errors.append(
                f"diagram {diagram['key']} object {object_id} has no explicit layout"
            )
            continue
        if obj.get("parent") == model_object and not box_contains(parent_area, layout):
            errors.append(
                f"diagram {diagram['key']} child object {object_id} is outside its parent area"
            )
        if obj.get("external") and box_intersects(parent_area, layout):
            errors.append(
                f"diagram {diagram['key']} external object {object_id} intersects its parent area"
            )
        if object_id in RUNTIME_GROUP_IDS and not box_contains(parent_area, layout):
            errors.append(
                f"diagram {diagram['key']} runtime group {object_id} is outside its parent area"
            )
    return errors


def validate_runtime_groups(
    model: dict[str, Any],
    object_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    for obj in model["objects"]:
        runtime_groups = [group for group in obj.get("groups", []) if group in RUNTIME_GROUP_IDS]
        expected_group = RUNTIME_GROUP_BY_OBJECT.get(obj["id"])
        if expected_group and runtime_groups != [expected_group]:
            errors.append(
                f"object {obj['id']} must belong only to runtime group {expected_group}; got {runtime_groups}"
            )
        if not expected_group and runtime_groups:
            errors.append(f"object {obj['id']} has unexpected runtime groups: {runtime_groups}")

    support_members = sorted(
        obj["id"] for obj in model["objects"] if SUPPORT_GROUP_ID in (obj.get("groups") or [])
    )
    expected_support_members = sorted(
        object_id
        for object_id, group_id in RUNTIME_GROUP_BY_OBJECT.items()
        if group_id == SUPPORT_GROUP_ID
    )
    if support_members != expected_support_members:
        errors.append(
            "support-services group membership mismatch: "
            f"expected {expected_support_members}, got {support_members}"
        )

    runtime_diagrams = [diagram for diagram in model["diagrams"] if diagram["key"] == "runtime"]
    if runtime_diagrams:
        for object_id in runtime_diagrams[0]["objects"]:
            obj = object_by_id.get(object_id)
            if obj and obj.get("parent") == "DLH-L1-RUNTIME" and object_id not in RUNTIME_GROUP_BY_OBJECT:
                errors.append(f"runtime object {object_id} has no explicit runtime group policy")
    return errors


def box_contains(outer: dict[str, int], inner: dict[str, int]) -> bool:
    return (
        inner["x"] >= outer["x"]
        and inner["y"] >= outer["y"]
        and inner["x"] + inner["width"] <= outer["x"] + outer["width"]
        and inner["y"] + inner["height"] <= outer["y"] + outer["height"]
    )


def box_intersects(first: dict[str, int], second: dict[str, int]) -> bool:
    return not (
        second["x"] + second["width"] <= first["x"]
        or second["x"] >= first["x"] + first["width"]
        or second["y"] + second["height"] <= first["y"]
        or second["y"] >= first["y"] + first["height"]
    )


def box_intersects_with_padding(
    first: dict[str, int],
    second: dict[str, int],
    *,
    padding: int,
) -> bool:
    expanded = {
        "x": first["x"] - padding,
        "y": first["y"] - padding,
        "width": first["width"] + padding * 2,
        "height": first["height"] + padding * 2,
    }
    return box_intersects(expanded, second)


def connection_points_for_diagram(
    diagram_key: str,
    connection: dict[str, Any],
    origin_box: dict[str, int],
    target_box: dict[str, int],
) -> list[dict[str, float]]:
    route = (connection.get("layout") or {}).get(diagram_key)
    if route and route.get("points"):
        return [
            {"x": float(point["x"]), "y": float(point["y"])}
            for point in route["points"]
        ]
    return default_connection_points(origin_box, target_box)


def default_connection_points(
    origin_box: dict[str, int],
    target_box: dict[str, int],
) -> list[dict[str, float]]:
    ox = origin_box["x"] + origin_box["width"] / 2
    oy = origin_box["y"] + origin_box["height"] / 2
    tx = target_box["x"] + target_box["width"] / 2
    ty = target_box["y"] + target_box["height"] / 2
    if abs(tx - ox) >= abs(ty - oy):
        if tx >= ox:
            return [
                {"x": origin_box["x"] + origin_box["width"], "y": oy},
                {"x": target_box["x"], "y": ty},
            ]
        return [
            {"x": origin_box["x"], "y": oy},
            {"x": target_box["x"] + target_box["width"], "y": ty},
        ]
    if ty >= oy:
        return [
            {"x": ox, "y": origin_box["y"] + origin_box["height"]},
            {"x": tx, "y": target_box["y"]},
        ]
    return [
        {"x": ox, "y": origin_box["y"]},
        {"x": tx, "y": target_box["y"] + target_box["height"]},
    ]


def polyline_intersects_box(
    points: list[dict[str, float]],
    box: dict[str, int],
    *,
    padding: int,
) -> bool:
    expanded = {
        "x": box["x"] - padding,
        "y": box["y"] - padding,
        "width": box["width"] + padding * 2,
        "height": box["height"] + padding * 2,
    }
    for start, end in zip(points, points[1:]):
        if segment_intersects_box(start, end, expanded):
            return True
    return False


def segment_intersects_box(
    start: dict[str, float],
    end: dict[str, float],
    box: dict[str, int],
) -> bool:
    for step in range(1, 40):
        ratio = step / 40
        x = start["x"] + (end["x"] - start["x"]) * ratio
        y = start["y"] + (end["y"] - start["y"]) * ratio
        if box["x"] <= x <= box["x"] + box["width"] and box["y"] <= y <= box["y"] + box["height"]:
            return True
    return False


def github_main_path(url: str) -> str | None:
    if not url.startswith(GITHUB_REPO_URL):
        return None
    parsed = urlparse(url)
    parts = [unquote(part) for part in parsed.path.strip("/").split("/")]
    if len(parts) < 5 or parts[0] != "sanger-pathogens":
        return None
    if parts[1] != "dlh-in-a-box-umbrella-helm-chart":
        return None
    if parts[2] not in {"tree", "blob"} or parts[3] != "main":
        return None
    return "/".join(parts[4:])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", nargs="?", default=DEFAULT_MODEL)
    parser.add_argument("schema", nargs="?", default=DEFAULT_SCHEMA)
    parser.add_argument("--audit-links", action="store_true", help="Print objects without reality links")
    args = parser.parse_args()

    model_path = Path(args.model)
    schema_path = Path(args.schema)

    model = load_json(model_path)
    schema = load_json(schema_path)
    errors: list[str] = []
    validate_schema_node(model, schema, schema, "$", errors)
    errors.extend(validate_semantics(model))

    if errors:
        print(f"DLH IcePanel JSON validation failed: {model_path}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    if args.audit_links:
        print_link_audit(model)
    print(f"DLH IcePanel JSON validation ok: {model_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
