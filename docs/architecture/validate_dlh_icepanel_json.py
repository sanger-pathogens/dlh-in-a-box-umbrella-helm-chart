#!/usr/bin/env python3
"""Validate the DLH-in-a-box IcePanel JSON model.

This validator intentionally avoids third-party dependencies. It supports the
JSON Schema features used by dlh-in-a-box.schema.json and adds a semantic pass
for model references that JSON Schema alone does not express.
"""

from __future__ import annotations

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
            group = next(obj for obj in model["objects"] if obj["id"] == group_id)
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
        if item["target"] not in object_id_set:
            errors.append(f"connection {item['id']} target does not exist: {item['target']}")

    for item in model["diagrams"]:
        model_object = item.get("modelObject")
        if model_object is not None and model_object not in object_id_set:
            errors.append(f"diagram {item['key']} modelObject does not exist: {model_object}")
        for object_id in item["objects"]:
            if object_id not in object_id_set:
                errors.append(f"diagram {item['key']} object does not exist: {object_id}")
        for connection_id in item["connections"]:
            if connection_id not in connection_id_set:
                errors.append(f"diagram {item['key']} connection does not exist: {connection_id}")

    if len(model["diagrams"]) != 9:
        errors.append(f"expected 9 official diagrams, found {len(model['diagrams'])}")

    return errors


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
    model_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_MODEL
    schema_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_SCHEMA

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

    print(f"DLH IcePanel JSON validation ok: {model_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
