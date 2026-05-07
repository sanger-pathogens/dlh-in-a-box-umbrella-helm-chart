#!/usr/bin/env python3
"""Synchronize the DLH-in-a-box architecture model into IcePanel.

The script is intentionally conservative:

* the JSON model file is the source of truth for the official DLH diagrams;
* the Markdown parser is retained as a transition/import path;
* dry-run mode is the default;
* existing non-source objects, connections, and diagrams are left in place;
* existing IcePanel icons and technology IDs are preserved on matched objects.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


LANDSCAPE_ID = "puMOgHbuk4mQzX58wBMt"
VERSION_ID = "eCIlbt3z8AUfXq1bwtHf"
DOMAIN_ID = "56Ri7UsKptmjXd1bFylL"
API_BASE_URL = "https://api.icepanel.io/v1"
DEFAULT_JSON_SOURCE_FILE = "docs/architecture/icepanel/models/dlh-in-a-box.json"
MARKDOWN_SOURCE_FILE = "docs/architecture/dlh-in-a-box-icepanel-model.md"
ROOT_PARENT = "__ROOT__"
SOURCE_ID_LABEL = "dlhSourceId"
SOURCE_IDS_LABEL = "dlhSourceIds"
SOURCE_FILE_LABEL = "dlhSourceFile"
DIAGRAM_KEY_LABEL = "dlhDiagramKey"
SCHEMA_VERSION = 1

VISUAL_GROUP_MODEL_NAMES = {
    "DLH-G-chart-product-CHART-SOURCE": "Chart Source Boundary",
}

DIAGRAM_EXPORT_FILENAMES = {
    "context": "01-context.png",
    "chart-product": "02-chart-product-and-packaging.png",
    "runtime": "03-runtime-deployed-by-the-chart.png",
    "chart-source": "04-chart-source-components.png",
    "packaged-dependencies": "05-packaged-upstream-dependencies.png",
    "vendored-trino": "06-vendored-trino-chart.png",
    "hive-subchart": "07-hive-metastore-local-subchart.png",
    "validation": "08-chart-validation-automation.png",
    "publish": "09-chart-publish-automation.png",
}

DIAGRAM_BOUNDS = {
    "chart-product": {"x": -380, "y": -360, "width": 2580, "height": 900},
    "runtime": {"x": -420, "y": -980, "width": 2740, "height": 2000},
    "chart-source": {"x": 0, "y": 0, "width": 1480, "height": 840},
    "packaged-dependencies": {"x": 0, "y": 0, "width": 1480, "height": 660},
    "vendored-trino": {"x": 0, "y": 0, "width": 1480, "height": 460},
    "hive-subchart": {"x": 0, "y": 0, "width": 1480, "height": 460},
    "validation": {"x": 0, "y": 0, "width": 1480, "height": 460},
    "publish": {"x": 0, "y": 0, "width": 1160, "height": 360},
}

DEFAULT_DIAGRAM_BOUNDS = {"x": -160, "y": -160, "width": 1480, "height": 920}


@dataclass
class SourceObject:
    source_id: str
    name: str
    type: str
    parent_source_id: str
    description: str
    caption: str = ""
    status: str = "live"
    external: bool = False
    source_ids: list[str] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)
    layout: dict[str, dict[str, int]] = field(default_factory=dict)
    groups: list[str] = field(default_factory=list)
    links: list[dict[str, str]] = field(default_factory=list)
    tag_ids: list[str] = field(default_factory=list)
    team_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.source_ids:
            self.source_ids = [self.source_id]


@dataclass
class SourceConnection:
    source_id: str
    origin_source_id: str
    target_source_id: str
    label: str
    direction: str = "outgoing"
    source_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.source_ids:
            self.source_ids = [self.source_id]


@dataclass
class DiagramSpec:
    key: str
    name: str
    type: str
    model_source_id: str
    object_source_ids: list[str]
    connection_source_ids: list[str]
    description: str = ""
    export_filename: str = ""
    bounds: dict[str, int] = field(default_factory=dict)


@dataclass
class SourceModel:
    objects: dict[str, SourceObject]
    connections: dict[str, SourceConnection]
    diagrams: dict[str, DiagramSpec]
    aliases: dict[str, str]
    source_file: str = DEFAULT_JSON_SOURCE_FILE
    landscape_id: str = LANDSCAPE_ID
    version_id: str = VERSION_ID
    domain_id: str = DOMAIN_ID
    labels: dict[str, str] = field(
        default_factory=lambda: {
            "sourceId": SOURCE_ID_LABEL,
            "sourceIds": SOURCE_IDS_LABEL,
            "sourceFile": SOURCE_FILE_LABEL,
            "diagramKey": DIAGRAM_KEY_LABEL,
        }
    )


class IcePanelClient:
    def __init__(self, api_key: str, dry_run: bool) -> None:
        self.api_key = api_key
        self.dry_run = dry_run

    def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{API_BASE_URL}{path}"
        data = None
        headers = {
            "Accept": "application/json",
            "X-API-Key": self.api_key,
        }
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = response.read()
        except urllib.error.HTTPError as exc:
            payload = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"IcePanel API {method} {path} failed with {exc.code}: {payload}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"IcePanel API {method} {path} failed: {exc}") from exc

        if not payload:
            return {}
        return json.loads(payload.decode("utf-8"))

    def get(self, path: str) -> dict[str, Any]:
        return self.request("GET", path)

    def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", path, body)

    def patch(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        return self.request("PATCH", path, body)

    def put(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        return self.request("PUT", path, body)


def clean_cell(value: str) -> str:
    value = value.strip()
    value = value.replace("<br>", "; ").replace("<br/>", "; ").replace("<br />", "; ")
    value = re.sub(r"\s+", " ", value)
    if len(value) >= 2 and value[0] == "`" and value[-1] == "`":
        value = value[1:-1]
    return value.strip()


def split_table_row(line: str) -> list[str]:
    return [clean_cell(cell) for cell in line.strip().strip("|").split("|")]


def parse_markdown_table(lines: list[str], start: int) -> tuple[list[dict[str, str]], int]:
    table_lines: list[str] = []
    index = start
    while index < len(lines) and lines[index].lstrip().startswith("|"):
        table_lines.append(lines[index])
        index += 1
    if len(table_lines) < 2:
        return [], index

    headers = split_table_row(table_lines[0])
    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        cells = split_table_row(line)
        if len(cells) < len(headers):
            cells.extend([""] * (len(headers) - len(cells)))
        rows.append(dict(zip(headers, cells)))
    return rows, index


def table_after(block: str, heading: str) -> list[dict[str, str]]:
    pattern = re.compile(rf"^###\s+{re.escape(heading)}\s*$", re.MULTILINE)
    match = pattern.search(block)
    if not match:
        return []
    lines = block[match.end() :].splitlines()
    for index, line in enumerate(lines):
        if line.lstrip().startswith("|"):
            rows, _ = parse_markdown_table(lines, index)
            return rows
        if line.startswith("### ") or line.startswith("## "):
            return []
    return []


def section_after(block: str, heading: str) -> str:
    pattern = re.compile(rf"^###\s+{re.escape(heading)}\s*$", re.MULTILINE)
    match = pattern.search(block)
    if not match:
        return ""
    tail = block[match.end() :]
    next_heading = re.search(r"^###\s+", tail, re.MULTILINE)
    if next_heading:
        tail = tail[: next_heading.start()]
    return tail.strip()


def h2_sections(text: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", text, re.MULTILINE))
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((match.group(1).strip(), text[match.end() : end]))
    return sections


def normalize_type(value: str) -> str:
    return clean_cell(value).lower().replace("icepanel type", "").strip()


def normalize_status(value: str) -> str:
    status = clean_cell(value).lower()
    if status in {"deprecated", "future", "live", "removed"}:
        return status
    return "live"


def source_connection_id(origin: str, target: str, label: str) -> str:
    digest = hashlib.sha1(f"{origin}|{target}|{label}".encode("utf-8")).hexdigest()[:12]
    return f"DLH-CONN-{digest}"


def slug(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")
    return value.upper() or "GROUP"


def add_object(objects: dict[str, SourceObject], obj: SourceObject) -> None:
    if obj.source_id in objects:
        raise ValueError(f"Duplicate source object ID: {obj.source_id}")
    objects[obj.source_id] = obj


def object_from_row(
    row: dict[str, str],
    parent_source_id: str,
    *,
    default_type: str | None = None,
    external: bool = False,
    extra_labels: dict[str, str] | None = None,
) -> SourceObject:
    labels: dict[str, str] = {}
    if extra_labels:
        labels.update(extra_labels)

    path = row.get("Path", "")
    if path:
        labels["dlhPath"] = path
    technology = row.get("Technology", "")
    if technology:
        labels["dlhTechnology"] = technology
    enabled_by = row.get("Enabled By", "")
    if enabled_by:
        labels["dlhEnabledBy"] = enabled_by
    default = row.get("Default", "")
    if default:
        labels["dlhDefault"] = default

    source_id = row["ID"]
    name = row["Name"]
    type_value = normalize_type(row.get("IcePanel Type", default_type or "Component"))
    description = row.get("Description", "")
    status = normalize_status(row.get("Status", "live"))
    return SourceObject(
        source_id=source_id,
        name=name,
        type=type_value,
        parent_source_id=parent_source_id,
        description=description,
        status=status,
        external=external,
        labels=labels,
    )


def add_relationships(
    rows: list[dict[str, str]],
    connections: dict[str, SourceConnection],
) -> list[str]:
    connection_ids: list[str] = []
    for row in rows:
        origin = row["From"]
        target = row["To"]
        label = row["Label"]
        connection_id = source_connection_id(origin, target, label)
        if connection_id not in connections:
            connections[connection_id] = SourceConnection(
                source_id=connection_id,
                origin_source_id=origin,
                target_source_id=target,
                label=label,
            )
        connection_ids.append(connection_id)
    return connection_ids


def add_visual_groups(
    rows: list[dict[str, str]],
    objects: dict[str, SourceObject],
    diagram_key: str,
    parent_source_id: str,
) -> list[str]:
    group_ids: list[str] = []
    for row in rows:
        name = row["Group"]
        source_id = f"DLH-G-{diagram_key}-{slug(name)}"
        model_name = VISUAL_GROUP_MODEL_NAMES.get(source_id, name)
        contains = row.get("Contains", "")
        notes = row.get("Notes", "")
        parts = [part for part in [notes, f"Contains: {contains}" if contains else ""] if part]
        description = ". ".join(parts).rstrip(".") + "."
        if source_id not in objects:
            add_object(
                objects,
                SourceObject(
                    source_id=source_id,
                    name=model_name,
                    type="group",
                    parent_source_id=parent_source_id,
                    description=description,
                    status="live",
                    labels={"dlhVisualGroup": "true"},
                ),
            )
        group_ids.append(source_id)
    return group_ids


def parse_source_model(path: Path) -> SourceModel:
    text = path.read_text(encoding="utf-8")
    objects: dict[str, SourceObject] = {}
    connections: dict[str, SourceConnection] = {}
    diagrams: dict[str, DiagramSpec] = {}

    for title, block in h2_sections(text):
        if title == "Level 1 Context Diagram":
            object_ids: list[str] = []
            for row in table_after(block, "Objects"):
                add_object(
                    objects,
                    object_from_row(row, ROOT_PARENT, external=row["ID"] == "DLH-L1-UPSTREAM-DEPS"),
                )
                object_ids.append(row["ID"])
            relationship_ids = add_relationships(table_after(block, "Relationships"), connections)
            diagrams["context"] = DiagramSpec(
                key="context",
                name="Context Diagram",
                type="context-diagram",
                model_source_id=ROOT_PARENT,
                object_source_ids=object_ids,
                connection_source_ids=relationship_ids,
                description=section_after(block, "Figure Caption"),
            )

        elif title == "Level 2 Container Diagram A: Chart Product And Packaging":
            object_ids = []
            group_ids = add_visual_groups(
                table_after(block, "Visual Groups"),
                objects,
                "chart-product",
                ROOT_PARENT,
            )
            for row in table_after(block, "Internal Apps And Stores"):
                add_object(objects, object_from_row(row, "DLH-L1-CHART"))
                object_ids.append(row["ID"])
            for row in table_after(block, "External Systems"):
                add_object(objects, object_from_row(row, ROOT_PARENT, external=True))
                object_ids.append(row["ID"])
            relationship_ids = add_relationships(table_after(block, "Relationships"), connections)
            diagrams["chart-product"] = DiagramSpec(
                key="chart-product",
                name="Chart Product And Packaging",
                type="app-diagram",
                model_source_id="DLH-L1-CHART",
                object_source_ids=group_ids + object_ids,
                connection_source_ids=relationship_ids,
                description=(
                    "Helm chart source, packaged dependencies, examples, automation, "
                    "and the published artifact used by deployment repositories."
                ),
            )

        elif title == "Level 2 Container Diagram B: Runtime Deployed By The Chart":
            object_ids = []
            group_ids = add_visual_groups(
                table_after(block, "Visual Groups"),
                objects,
                "runtime",
                ROOT_PARENT,
            )
            for row in table_after(block, "Deployed Apps And Stores"):
                add_object(objects, object_from_row(row, "DLH-L1-RUNTIME"))
                object_ids.append(row["ID"])
            for row in table_after(block, "External Runtime Context"):
                add_object(objects, object_from_row(row, ROOT_PARENT, external=True))
                object_ids.append(row["ID"])
            relationship_ids = add_relationships(
                table_after(block, "Runtime Relationships"),
                connections,
            )
            diagrams["runtime"] = DiagramSpec(
                key="runtime",
                name="Runtime Deployed By The Chart",
                type="app-diagram",
                model_source_id="DLH-L1-RUNTIME",
                object_source_ids=group_ids + object_ids,
                connection_source_ids=relationship_ids,
                description=(
                    "Generic DLH-in-a-box runtime deployed by the chart, including "
                    "core lakehouse services, optional applications, and external context."
                ),
            )

        elif title == "Level 3 Component Diagram A: Chart Source":
            parent = extract_parent_source_id(block)
            component_ids = []
            for row in table_after(block, "Components"):
                add_object(objects, object_from_row(row, parent, default_type="Component"))
                component_ids.append(row["ID"])
            relationship_ids = add_relationships(table_after(block, "Relationships"), connections)
            diagrams["chart-source"] = DiagramSpec(
                key="chart-source",
                name="Chart Source Components",
                type="component-diagram",
                model_source_id=parent,
                object_source_ids=component_ids,
                connection_source_ids=relationship_ids,
                description="Repository-owned chart files and templates that render the deployable package.",
            )

        elif title == "Level 3 Component Diagram B: Packaged Upstream Dependencies":
            parent = extract_parent_source_id(block)
            component_ids = []
            for row in table_after(block, "Components"):
                add_object(objects, object_from_row(row, parent, default_type="Component"))
                component_ids.append(row["ID"])
            diagrams["packaged-dependencies"] = DiagramSpec(
                key="packaged-dependencies",
                name="Packaged Upstream Dependencies",
                type="component-diagram",
                model_source_id=parent,
                object_source_ids=component_ids,
                connection_source_ids=[],
                description="Bundled upstream Helm archives included with the umbrella chart.",
            )

        elif title == "Level 3 Component Diagram C: Vendored Trino Chart":
            parent = extract_parent_source_id(block)
            component_ids = []
            for row in table_after(block, "Components"):
                add_object(objects, object_from_row(row, parent, default_type="Component"))
                component_ids.append(row["ID"])
            relationship_ids = add_relationships(table_after(block, "Relationships"), connections)
            diagrams["vendored-trino"] = DiagramSpec(
                key="vendored-trino",
                name="Vendored Trino Chart",
                type="component-diagram",
                model_source_id=parent,
                object_source_ids=component_ids,
                connection_source_ids=relationship_ids,
                description="Local Trino chart adaptations used for DLH-in-a-box integration.",
            )

        elif title == "Level 3 Component Diagram D: Hive Metastore Local Subchart":
            parent = extract_parent_source_id(block)
            component_ids = []
            for row in table_after(block, "Components"):
                add_object(objects, object_from_row(row, parent, default_type="Component"))
                component_ids.append(row["ID"])
            relationship_ids = add_relationships(table_after(block, "Relationships"), connections)
            diagrams["hive-subchart"] = DiagramSpec(
                key="hive-subchart",
                name="Hive Metastore Local Subchart",
                type="component-diagram",
                model_source_id=parent,
                object_source_ids=component_ids,
                connection_source_ids=relationship_ids,
                description="First-party Hive Metastore subchart components.",
            )

        elif title == "Level 3 Component Diagram E: Validation And Publish Automation":
            validation_ids = []
            for row in table_after(block, "Validation Components"):
                add_object(objects, object_from_row(row, row["Parent"], default_type="Component"))
                validation_ids.append(row["ID"])
            publish_ids = []
            for row in table_after(block, "Publish Components"):
                add_object(objects, object_from_row(row, row["Parent"], default_type="Component"))
                publish_ids.append(row["ID"])
            all_relationship_ids = add_relationships(table_after(block, "Relationships"), connections)
            validation_relationship_ids = [
                connection_id
                for connection_id in all_relationship_ids
                if connections[connection_id].origin_source_id.startswith("DLH-C3-VALIDATE")
            ]
            publish_relationship_ids = [
                connection_id
                for connection_id in all_relationship_ids
                if connections[connection_id].origin_source_id.startswith("DLH-C3-PUBLISH")
            ]
            diagrams["validation"] = DiagramSpec(
                key="validation",
                name="Chart Validation Automation",
                type="component-diagram",
                model_source_id="DLH-C2-VALIDATION",
                object_source_ids=validation_ids,
                connection_source_ids=validation_relationship_ids,
                description="Automated checks that test the chart before publication.",
            )
            diagrams["publish"] = DiagramSpec(
                key="publish",
                name="Chart Publish Automation",
                type="component-diagram",
                model_source_id="DLH-C2-PUBLISH",
                object_source_ids=publish_ids,
                connection_source_ids=publish_relationship_ids,
                description="Release automation that packages and publishes the Helm artifact.",
            )

    return canonicalize_source_model(objects, connections, diagrams)


def extract_parent_source_id(block: str) -> str:
    match = re.search(r"Parent Level 2 object:\s+`([^`]+)`", block)
    if not match:
        match = re.search(r"Parent Level 2 objects:\s+`([^`]+)`", block)
    if not match:
        raise ValueError("Could not find parent source ID for component diagram")
    return match.group(1)


def canonicalize_source_model(
    objects: dict[str, SourceObject],
    connections: dict[str, SourceConnection],
    diagrams: dict[str, DiagramSpec],
) -> SourceModel:
    aliases: dict[str, str] = {}
    canonical_by_key: dict[tuple[str, str, str], str] = {}
    canonical_objects: dict[str, SourceObject] = {}

    for source_id, obj in objects.items():
        parent = aliases.get(obj.parent_source_id, obj.parent_source_id)
        key = (parent, obj.type, obj.name.casefold())
        if key in canonical_by_key:
            canonical_id = canonical_by_key[key]
            aliases[source_id] = canonical_id
            canonical_objects[canonical_id].source_ids.append(source_id)
            continue
        obj.parent_source_id = parent
        canonical_by_key[key] = source_id
        aliases[source_id] = source_id
        canonical_objects[source_id] = obj

    canonical_connections: dict[str, SourceConnection] = {}
    canonical_connection_by_key: dict[tuple[str, str, str], str] = {}
    connection_aliases: dict[str, str] = {}
    for source_id, connection in connections.items():
        origin = aliases.get(connection.origin_source_id, connection.origin_source_id)
        target = aliases.get(connection.target_source_id, connection.target_source_id)
        key = (origin, target, connection.label)
        if key in canonical_connection_by_key:
            canonical_id = canonical_connection_by_key[key]
            connection_aliases[source_id] = canonical_id
            canonical_connections[canonical_id].source_ids.append(source_id)
            continue
        connection.origin_source_id = origin
        connection.target_source_id = target
        canonical_connection_by_key[key] = source_id
        connection_aliases[source_id] = source_id
        canonical_connections[source_id] = connection

    canonical_diagrams: dict[str, DiagramSpec] = {}
    for key, diagram in diagrams.items():
        object_ids = unique_preserving_order(
            aliases.get(source_id, source_id) for source_id in diagram.object_source_ids
        )
        connection_ids = unique_preserving_order(
            connection_aliases.get(source_id, source_id)
            for source_id in diagram.connection_source_ids
        )
        model_source_id = aliases.get(diagram.model_source_id, diagram.model_source_id)
        canonical_diagrams[key] = DiagramSpec(
            key=diagram.key,
            name=diagram.name,
            type=diagram.type,
            model_source_id=model_source_id,
            object_source_ids=object_ids,
            connection_source_ids=connection_ids,
            description=diagram.description,
            export_filename=diagram.export_filename
            or DIAGRAM_EXPORT_FILENAMES.get(diagram.key, f"{diagram.key}.png"),
            bounds=diagram.bounds or DIAGRAM_BOUNDS.get(diagram.key, DEFAULT_DIAGRAM_BOUNDS),
        )

    return SourceModel(
        objects=canonical_objects,
        connections=canonical_connections,
        diagrams=canonical_diagrams,
        aliases=aliases,
    )


def unique_preserving_order(values: Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def load_source_model(path: Path, source_format: str) -> SourceModel:
    if source_format == "auto":
        source_format = "json" if path.suffix.lower() == ".json" else "markdown"
    if source_format == "json":
        return parse_json_source_model(path)
    if source_format == "markdown":
        source = parse_source_model(path)
        source.source_file = MARKDOWN_SOURCE_FILE
        return source
    raise ValueError(f"Unsupported source format: {source_format}")


def parse_json_source_model(path: Path) -> SourceModel:
    payload = json.loads(path.read_text(encoding="utf-8"))
    icepanel = payload.get("icepanel") or {}
    label_config = icepanel.get("labels") or {}
    source_file = label_config.get("sourceFileValue") or relative_path(path)

    objects: dict[str, SourceObject] = {}
    for item in payload.get("objects", []):
        add_object(
            objects,
            SourceObject(
                source_id=item["id"],
                name=item["name"],
                type=item["type"],
                parent_source_id=item.get("parent") or ROOT_PARENT,
                description=item.get("description", ""),
                caption=item.get("caption", "") or item.get("description", ""),
                status=item.get("status", "live"),
                external=bool(item.get("external", False)),
                source_ids=list(item.get("sourceIds") or [item["id"]]),
                labels={str(k): str(v) for k, v in (item.get("labels") or {}).items()},
                layout=normalize_layout(item.get("layout") or {}),
                groups=list(item.get("groups") or []),
                links=[
                    {str(k): str(v) for k, v in link.items()}
                    for link in (item.get("links") or [])
                ],
                tag_ids=list(item.get("tagIds") or []),
                team_ids=list(item.get("teamIds") or []),
            ),
        )

    connections: dict[str, SourceConnection] = {}
    for item in payload.get("connections", []):
        connections[item["id"]] = SourceConnection(
            source_id=item["id"],
            origin_source_id=item["origin"],
            target_source_id=item["target"],
            label=item["label"],
            direction=item.get("direction", "outgoing"),
            source_ids=list(item.get("sourceIds") or [item["id"]]),
        )

    diagrams: dict[str, DiagramSpec] = {}
    for item in payload.get("diagrams", []):
        diagrams[item["key"]] = DiagramSpec(
            key=item["key"],
            name=item["name"],
            type=item["type"],
            model_source_id=item.get("modelObject") or ROOT_PARENT,
            object_source_ids=list(item.get("objects") or []),
            connection_source_ids=list(item.get("connections") or []),
            description=item.get("description", ""),
            export_filename=item.get("exportFilename", ""),
            bounds=normalize_bounds(item.get("bounds") or {}),
        )

    source = canonicalize_source_model(objects, connections, diagrams)
    source.source_file = source_file
    source.landscape_id = icepanel.get("landscapeId", LANDSCAPE_ID)
    source.version_id = icepanel.get("versionId", VERSION_ID)
    source.domain_id = icepanel.get("domainId", DOMAIN_ID)
    source.labels = {
        "sourceId": label_config.get("sourceId", SOURCE_ID_LABEL),
        "sourceIds": label_config.get("sourceIds", SOURCE_IDS_LABEL),
        "sourceFile": label_config.get("sourceFile", SOURCE_FILE_LABEL),
        "diagramKey": label_config.get("diagramKey", DIAGRAM_KEY_LABEL),
    }
    return source


def normalize_layout(layout: dict[str, Any]) -> dict[str, dict[str, int]]:
    return {
        str(key): normalize_bounds(value)
        for key, value in layout.items()
        if isinstance(value, dict)
    }


def normalize_bounds(bounds: dict[str, Any]) -> dict[str, int]:
    normalized: dict[str, int] = {}
    for key in ("x", "y", "width", "height"):
        if key in bounds:
            normalized[key] = int(bounds[key])
    return normalized


def source_model_to_json(source: SourceModel, source_file: str) -> dict[str, Any]:
    objects = []
    for source_id, obj in source.objects.items():
        item: dict[str, Any] = {
            "id": source_id,
            "name": obj.name,
            "type": obj.type,
            "parent": None if obj.parent_source_id == ROOT_PARENT else obj.parent_source_id,
            "status": obj.status,
            "external": obj.external,
            "caption": obj.caption or obj.description,
            "description": obj.description,
            "labels": obj.labels,
            "layout": layout_for_object(source_id, obj),
        }
        if obj.groups:
            item["groups"] = obj.groups
        if obj.links:
            item["links"] = obj.links
        if obj.tag_ids:
            item["tagIds"] = obj.tag_ids
        if obj.team_ids:
            item["teamIds"] = obj.team_ids
        if obj.source_ids != [source_id]:
            item["sourceIds"] = obj.source_ids
        objects.append(item)

    connections = []
    for source_id, connection in source.connections.items():
        item = {
            "id": source_id,
            "origin": connection.origin_source_id,
            "target": connection.target_source_id,
            "label": connection.label,
            "direction": connection.direction,
        }
        if connection.source_ids != [source_id]:
            item["sourceIds"] = connection.source_ids
        connections.append(item)

    diagrams = []
    for key, diagram in source.diagrams.items():
        diagrams.append(
            {
                "key": key,
                "name": diagram.name,
                "type": diagram.type,
                "modelObject": None
                if diagram.model_source_id == ROOT_PARENT
                else diagram.model_source_id,
                "objects": diagram.object_source_ids,
                "connections": diagram.connection_source_ids,
                "description": diagram.description,
                "bounds": diagram.bounds or DIAGRAM_BOUNDS.get(key, DEFAULT_DIAGRAM_BOUNDS),
                "exportFilename": diagram.export_filename
                or DIAGRAM_EXPORT_FILENAMES.get(key, f"{key}.png"),
            }
        )

    return {
        "$schema": "./dlh-in-a-box.schema.json",
        "schemaVersion": SCHEMA_VERSION,
        "icepanel": {
            "landscapeId": LANDSCAPE_ID,
            "versionId": VERSION_ID,
            "domainId": DOMAIN_ID,
            "apiBaseUrl": API_BASE_URL,
            "labels": {
                "sourceId": SOURCE_ID_LABEL,
                "sourceIds": SOURCE_IDS_LABEL,
                "sourceFile": SOURCE_FILE_LABEL,
                "diagramKey": DIAGRAM_KEY_LABEL,
                "sourceFileValue": source_file,
            },
        },
        "objects": objects,
        "connections": connections,
        "diagrams": diagrams,
    }


def layout_for_object(source_id: str, obj: SourceObject) -> dict[str, dict[str, int]]:
    layout = dict(obj.layout)
    for diagram_key, positions in EXPLICIT_POSITIONS.items():
        if source_id in positions:
            layout[diagram_key] = positions[source_id]
    for diagram_key, positions in EXPLICIT_GROUP_POSITIONS.items():
        if source_id in positions:
            layout[diagram_key] = positions[source_id]
    return layout


def write_json_source_model(source: SourceModel, path: Path, source_file: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = source_model_to_json(source, source_file)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def parse_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        env[key] = value
    return env


def load_api_key(repo_root: Path) -> str:
    if os.environ.get("ICEPANEL_API_KEY"):
        return os.environ["ICEPANEL_API_KEY"]
    env = parse_env_file(repo_root / ".env")
    api_key = env.get("ICEPANEL_API_KEY")
    if not api_key:
        raise RuntimeError("ICEPANEL_API_KEY is not set in the environment or root .env")
    return api_key


def list_response(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise RuntimeError(f"Unexpected IcePanel response shape; missing list key {key!r}")
    return value


def labels_contain_source_id(
    labels: dict[str, Any],
    source_id: str,
    label_keys: dict[str, str] | None = None,
) -> bool:
    label_keys = label_keys or {
        "sourceId": SOURCE_ID_LABEL,
        "sourceIds": SOURCE_IDS_LABEL,
    }
    ids = set()
    if labels.get(label_keys["sourceId"]):
        ids.add(str(labels[label_keys["sourceId"]]))
    if labels.get(label_keys["sourceIds"]):
        ids.update(part.strip() for part in str(labels[label_keys["sourceIds"]]).split(","))
    return source_id in ids


def merge_labels(existing: dict[str, Any], desired: dict[str, str]) -> dict[str, str]:
    merged = {str(key): str(value) for key, value in (existing or {}).items()}
    merged.update(desired)
    return merged


def reality_link_id(source_id: str, url: str) -> str:
    digest = hashlib.sha1(f"{source_id}|{url}".encode("utf-8")).hexdigest()
    return f"dlh{digest[:17]}"


def desired_object_links(obj: SourceObject) -> dict[str, dict[str, Any]]:
    links: dict[str, dict[str, Any]] = {}
    for index, link in enumerate(obj.links):
        url = link.get("url", "").strip()
        if not url:
            continue
        link_id = reality_link_id(obj.source_id, url)
        links[link_id] = {
            "id": link_id,
            "index": index,
            "customName": link.get("name") or "GitHub source",
            "connectionResolveUrl": url,
            "url": url,
        }
    return links


def desired_links_patch(
    existing: dict[str, Any],
    desired: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    existing_links = existing.get("links") or {}
    add: dict[str, dict[str, Any]] = {}
    update: dict[str, dict[str, Any]] = {}
    remove: list[str] = []

    desired_ids = set(desired)
    for link_id, link in desired.items():
        current = existing_links.get(link_id)
        if current is None:
            add[link_id] = link
            continue
        comparable = {
            "id": current.get("id"),
            "index": current.get("index"),
            "customName": current.get("customName"),
            "connectionResolveUrl": current.get("connectionResolveUrl"),
            "url": current.get("url"),
        }
        if comparable != link:
            update[link_id] = link

    for link_id in existing_links:
        if str(link_id).startswith("dlh") and link_id not in desired_ids:
            remove.append(link_id)

    if not add and not update and not remove:
        return None
    patch: dict[str, Any] = {}
    if add:
        patch["$add"] = add
    if update:
        patch["$update"] = update
    if remove:
        patch["$remove"] = sorted(remove)
    return patch


def desired_object_labels(obj: SourceObject, source: SourceModel) -> dict[str, str]:
    labels = {
        source.labels["sourceId"]: obj.source_id,
        source.labels["sourceIds"]: ",".join(obj.source_ids),
        source.labels["sourceFile"]: source.source_file,
    }
    labels.update(obj.labels)
    return labels


def desired_connection_labels(
    connection: SourceConnection,
    source: SourceModel,
) -> dict[str, str]:
    return {
        source.labels["sourceId"]: connection.source_id,
        source.labels["sourceIds"]: ",".join(connection.source_ids),
        source.labels["sourceFile"]: source.source_file,
    }


def desired_diagram_labels(diagram: DiagramSpec, source: SourceModel) -> dict[str, str]:
    return {
        source.labels["diagramKey"]: diagram.key,
        source.labels["sourceFile"]: source.source_file,
    }


LEGACY_OBJECT_NAMES_BY_SOURCE_ID: dict[str, list[str]] = {
    "DLH-L1-CHART": ["dlh-in-a-box Umbrella Helm Chart"],
    "DLH-X-INGRESS-CONTROLLER": ["DLH Ingress Controller"],
    "DLH-X-SECRET-SYNC": ["Secret Sync Substrate"],
    "DLH-R-MINIO": ["Minio"],
    "DLH-R-JUPYTER-PODS": ["Jupyter Notebook Pods"],
    "DLH-R-DATAHUB": ["Datahub app", "Datahub"],
    "DLH-R-DATAHUB-MYSQL": ["Datahub Database"],
    "DLH-R-DATAHUB-KAFKA": ["Datahub Event Stream"],
    "DLH-R-DATAHUB-ELASTICSEARCH": ["Datahub Search Index"],
    "DLH-X-LDAP": ["External LDAP/AD Directory", "External LDAP/ AD Directory"],
}

LEGACY_DIAGRAM_KEYS: dict[str, list[tuple[str, str]]] = {
    "context": [("Context Diagram", "context-diagram")],
    "runtime": [("Data Lakehouse App Diagram", "app-diagram")],
}


class SyncRunner:
    def __init__(
        self,
        repo_root: Path,
        client: IcePanelClient,
        source: SourceModel,
        *,
        update_layout: bool = False,
    ) -> None:
        self.repo_root = repo_root
        self.client = client
        self.source = source
        self.update_layout = update_layout
        self.objects: list[dict[str, Any]] = []
        self.connections: list[dict[str, Any]] = []
        self.diagrams: list[dict[str, Any]] = []
        self.source_to_object_id: dict[str, str] = {}
        self.source_to_connection_id: dict[str, str] = {}
        self.diagram_key_to_id: dict[str, str] = {}
        self.root_object_id = ""
        self.changes: list[str] = []

    def fetch_state(self) -> None:
        self.objects = list_response(
            self.client.get(
                f"/landscapes/{self.source.landscape_id}/versions/{self.source.version_id}/model/objects"
            ),
            "modelObjects",
        )
        self.connections = list_response(
            self.client.get(
                f"/landscapes/{self.source.landscape_id}/versions/{self.source.version_id}/model/connections"
            ),
            "modelConnections",
        )
        self.diagrams = list_response(
            self.client.get(
                f"/landscapes/{self.source.landscape_id}/versions/{self.source.version_id}/diagrams"
            ),
            "diagrams",
        )
        self.root_object_id = self.find_root_object_id()
        self.source_to_object_id[ROOT_PARENT] = self.root_object_id

    def find_root_object_id(self) -> str:
        candidates = [
            obj
            for obj in self.objects
            if obj.get("domainId") == self.source.domain_id
            and obj.get("type") == "root"
            and obj.get("parentId") is None
        ]
        if len(candidates) != 1:
            raise RuntimeError(
                f"Expected exactly one DLH domain root object, found {len(candidates)}"
            )
        return candidates[0]["id"]

    def run(self) -> None:
        self.fetch_state()
        self.sync_objects()
        self.sync_connections()
        self.sync_diagrams()
        self.sync_diagram_content()

    def object_depth(self, source_id: str, memo: dict[str, int] | None = None) -> int:
        if memo is None:
            memo = {}
        if source_id in memo:
            return memo[source_id]
        obj = self.source.objects[source_id]
        if obj.parent_source_id == ROOT_PARENT:
            memo[source_id] = 1
        else:
            memo[source_id] = 1 + self.object_depth(obj.parent_source_id, memo)
        return memo[source_id]

    def sync_objects(self) -> None:
        for source_id in sorted(self.source.objects, key=self.object_depth):
            obj = self.source.objects[source_id]
            parent_id = self.source_to_object_id.get(obj.parent_source_id)
            if not parent_id:
                raise RuntimeError(f"Parent object {obj.parent_source_id} has not been synced")
            existing = self.find_existing_object(obj, parent_id)
            if existing:
                self.source_to_object_id[source_id] = existing["id"]
                self.update_object_if_needed(existing, obj, parent_id)
            else:
                self.create_object(obj, parent_id)

    def find_existing_object(
        self,
        source_obj: SourceObject,
        desired_parent_id: str,
    ) -> dict[str, Any] | None:
        for obj in self.objects:
            if obj.get("domainId") != DOMAIN_ID:
                continue
            if labels_contain_source_id(
                obj.get("labels") or {}, source_obj.source_id, self.source.labels
            ):
                return obj

        names = [source_obj.name] + LEGACY_OBJECT_NAMES_BY_SOURCE_ID.get(
            source_obj.source_id, []
        )
        name_set = {name.casefold() for name in names}
        exact_parent = [
            obj
            for obj in self.objects
            if obj.get("domainId") == self.source.domain_id
            and obj.get("type") == source_obj.type
            and obj.get("parentId") == desired_parent_id
            and str(obj.get("name", "")).casefold() in name_set
        ]
        if len(exact_parent) == 1:
            return exact_parent[0]

        allow_reparent_match = source_obj.parent_source_id == "DLH-L1-RUNTIME"
        allow_reparent_match = allow_reparent_match or bool(
            LEGACY_OBJECT_NAMES_BY_SOURCE_ID.get(source_obj.source_id)
        )
        if allow_reparent_match:
            same_domain = [
                obj
                for obj in self.objects
                if obj.get("domainId") == self.source.domain_id
                and obj.get("type") == source_obj.type
                and str(obj.get("name", "")).casefold() in name_set
            ]
            if len(same_domain) == 1:
                return same_domain[0]
        return None

    def update_object_if_needed(
        self,
        existing: dict[str, Any],
        desired: SourceObject,
        desired_parent_id: str,
    ) -> None:
        payload: dict[str, Any] = {}
        fields: dict[str, Any] = {
            "name": desired.name,
            "type": desired.type,
            "parentId": desired_parent_id,
            "status": desired.status,
            "external": desired.external,
            "caption": desired.caption or desired.description,
            "description": desired.description,
        }
        for key, value in fields.items():
            if existing.get(key) != value:
                payload[key] = value
        labels = merge_labels(
            existing.get("labels") or {}, desired_object_labels(desired, self.source)
        )
        if labels != {str(k): str(v) for k, v in (existing.get("labels") or {}).items()}:
            payload["labels"] = labels
        desired_group_ids = self.desired_group_ids(desired, existing.get("groupIds") or [])
        if sorted(existing.get("groupIds") or []) != sorted(desired_group_ids):
            payload["groupIds"] = desired_group_ids
        if desired.tag_ids and sorted(existing.get("tagIds") or []) != sorted(desired.tag_ids):
            payload["tagIds"] = desired.tag_ids
        if desired.team_ids and sorted(existing.get("teamIds") or []) != sorted(desired.team_ids):
            payload["teamIds"] = desired.team_ids
        link_patch = desired_links_patch(existing, desired_object_links(desired))
        if link_patch:
            payload["links"] = link_patch
        if not payload:
            return
        if self.client.dry_run:
            self.changes.append(f"UPDATE object {existing['id']} {existing.get('name')} -> {desired.name}")
            return
        response = self.client.patch(
            f"/landscapes/{self.source.landscape_id}/versions/{self.source.version_id}/model/objects/{existing['id']}",
            payload,
        )
        updated = response.get("modelObject", existing)
        self.replace_object(updated)
        self.changes.append(f"UPDATED object {updated['id']} {updated.get('name')}")

    def create_object(self, desired: SourceObject, parent_id: str) -> None:
        payload = {
            "name": desired.name,
            "type": desired.type,
            "parentId": parent_id,
            "domainId": self.source.domain_id,
            "status": desired.status,
            "external": desired.external,
            "caption": desired.caption or desired.description,
            "description": desired.description,
            "labels": desired_object_labels(desired, self.source),
        }
        if desired.tag_ids:
            payload["tagIds"] = desired.tag_ids
        if desired.team_ids:
            payload["teamIds"] = desired.team_ids
        desired_group_ids = self.desired_group_ids(desired, [])
        if desired_group_ids:
            payload["groupIds"] = desired_group_ids
        desired_links = desired_object_links(desired)
        if desired_links:
            payload["links"] = desired_links
        if self.client.dry_run:
            fake_id = f"dry-object-{desired.source_id}"
            self.source_to_object_id[desired.source_id] = fake_id
            self.changes.append(f"CREATE object {desired.source_id} {desired.name}")
            return
        response = self.client.post(
            f"/landscapes/{self.source.landscape_id}/versions/{self.source.version_id}/model/objects",
            payload,
        )
        created = response["modelObject"]
        self.objects.append(created)
        self.source_to_object_id[desired.source_id] = created["id"]
        self.changes.append(f"CREATED object {created['id']} {created.get('name')}")

    def replace_object(self, updated: dict[str, Any]) -> None:
        self.objects = [updated if obj["id"] == updated["id"] else obj for obj in self.objects]

    def desired_group_ids(self, desired: SourceObject, existing_group_ids: list[str]) -> list[str]:
        if desired.type == "group":
            return list(existing_group_ids or [])
        source_group_ids = {
            self.source_to_object_id[source_id]
            for source_id, obj in self.source.objects.items()
            if obj.type == "group" and source_id in self.source_to_object_id
        }
        preserved = [group_id for group_id in existing_group_ids if group_id not in source_group_ids]
        desired_ids = []
        for group_source_id in desired.groups:
            if group_source_id not in self.source_to_object_id:
                raise RuntimeError(
                    f"Group {group_source_id} must be synced before object {desired.source_id}"
                )
            desired_ids.append(self.source_to_object_id[group_source_id])
        return unique_preserving_order(preserved + desired_ids)

    def sync_connections(self) -> None:
        for source_id, connection in self.source.connections.items():
            origin_id = self.source_to_object_id[connection.origin_source_id]
            target_id = self.source_to_object_id[connection.target_source_id]
            existing = self.find_existing_connection(connection, origin_id, target_id)
            if existing:
                self.source_to_connection_id[source_id] = existing["id"]
                self.update_connection_if_needed(existing, connection, origin_id, target_id)
            else:
                self.create_connection(connection, origin_id, target_id)

    def find_existing_connection(
        self,
        source_connection: SourceConnection,
        origin_id: str,
        target_id: str,
    ) -> dict[str, Any] | None:
        for connection in self.connections:
            if labels_contain_source_id(
                connection.get("labels") or {},
                source_connection.source_id,
                self.source.labels,
            ):
                return connection
        exact = [
            connection
            for connection in self.connections
            if connection.get("originId") == origin_id
            and connection.get("targetId") == target_id
            and connection.get("name") == source_connection.label
        ]
        if len(exact) == 1:
            return exact[0]
        endpoint_only = [
            connection
            for connection in self.connections
            if connection.get("originId") == origin_id
            and connection.get("targetId") == target_id
        ]
        if len(endpoint_only) == 1:
            return endpoint_only[0]
        return None

    def update_connection_if_needed(
        self,
        existing: dict[str, Any],
        desired: SourceConnection,
        origin_id: str,
        target_id: str,
    ) -> None:
        payload: dict[str, Any] = {}
        fields: dict[str, Any] = {
            "name": desired.label,
            "direction": desired.direction,
            "originId": origin_id,
            "targetId": target_id,
            "status": "live",
        }
        for key, value in fields.items():
            if existing.get(key) != value:
                payload[key] = value
        labels = merge_labels(
            existing.get("labels") or {}, desired_connection_labels(desired, self.source)
        )
        if labels != {str(k): str(v) for k, v in (existing.get("labels") or {}).items()}:
            payload["labels"] = labels
        if not payload:
            return
        if self.client.dry_run:
            self.changes.append(
                f"UPDATE connection {existing['id']} {existing.get('name')} -> {desired.label}"
            )
            return
        response = self.client.patch(
            f"/landscapes/{self.source.landscape_id}/versions/{self.source.version_id}/model/connections/{existing['id']}",
            payload,
        )
        updated = response.get("modelConnection", existing)
        self.replace_connection(updated)
        self.changes.append(f"UPDATED connection {updated['id']} {updated.get('name')}")

    def create_connection(
        self,
        desired: SourceConnection,
        origin_id: str,
        target_id: str,
    ) -> None:
        payload = {
            "name": desired.label,
            "direction": desired.direction,
            "originId": origin_id,
            "targetId": target_id,
            "status": "live",
            "labels": desired_connection_labels(desired, self.source),
        }
        if self.client.dry_run:
            fake_id = f"dry-connection-{desired.source_id}"
            self.source_to_connection_id[desired.source_id] = fake_id
            self.changes.append(
                f"CREATE connection {desired.origin_source_id} -> {desired.target_source_id}: {desired.label}"
            )
            return
        response = self.client.post(
            f"/landscapes/{self.source.landscape_id}/versions/{self.source.version_id}/model/connections",
            payload,
        )
        created = response["modelConnection"]
        self.connections.append(created)
        self.source_to_connection_id[desired.source_id] = created["id"]
        self.changes.append(f"CREATED connection {created['id']} {created.get('name')}")

    def replace_connection(self, updated: dict[str, Any]) -> None:
        self.connections = [
            updated if connection["id"] == updated["id"] else connection
            for connection in self.connections
        ]

    def sync_diagrams(self) -> None:
        for key, diagram in self.source.diagrams.items():
            model_id = (
                self.root_object_id
                if diagram.model_source_id == ROOT_PARENT
                else self.source_to_object_id[diagram.model_source_id]
            )
            existing = self.find_existing_diagram(diagram, model_id)
            if existing:
                self.diagram_key_to_id[key] = existing["id"]
                self.update_diagram_if_needed(existing, diagram, model_id)
            else:
                self.create_diagram(diagram, model_id)

    def find_existing_diagram(
        self,
        diagram: DiagramSpec,
        model_id: str,
    ) -> dict[str, Any] | None:
        for existing in self.diagrams:
            if (existing.get("labels") or {}).get(self.source.labels["diagramKey"]) == diagram.key:
                return existing
        exact = [
            existing
            for existing in self.diagrams
            if existing.get("name") == diagram.name
            and existing.get("type") == diagram.type
            and existing.get("modelId") == model_id
        ]
        if len(exact) == 1:
            return exact[0]
        for legacy_name, legacy_type in LEGACY_DIAGRAM_KEYS.get(diagram.key, []):
            legacy = [
                existing
                for existing in self.diagrams
                if existing.get("name") == legacy_name and existing.get("type") == legacy_type
            ]
            if len(legacy) == 1:
                return legacy[0]
        return None

    def update_diagram_if_needed(
        self,
        existing: dict[str, Any],
        desired: DiagramSpec,
        model_id: str,
    ) -> None:
        payload: dict[str, Any] = {}
        fields = {
            "name": self.desired_diagram_name(existing, desired),
            "type": desired.type,
            "modelId": model_id,
            "description": desired.description,
        }
        for key, value in fields.items():
            if existing.get(key) != value:
                payload[key] = value
        labels = merge_labels(
            existing.get("labels") or {}, desired_diagram_labels(desired, self.source)
        )
        if labels != {str(k): str(v) for k, v in (existing.get("labels") or {}).items()}:
            payload["labels"] = labels
        if not payload:
            return
        if self.client.dry_run:
            self.changes.append(f"UPDATE diagram {existing['id']} {existing.get('name')} -> {desired.name}")
            return
        response = self.client.patch(
            f"/landscapes/{self.source.landscape_id}/versions/{self.source.version_id}/diagrams/{existing['id']}",
            payload,
        )
        updated = response.get("diagram", existing)
        self.replace_diagram(updated)
        self.changes.append(f"UPDATED diagram {updated['id']} {updated.get('name')}")

    def create_diagram(self, desired: DiagramSpec, model_id: str) -> None:
        payload = {
            "name": desired.name,
            "type": desired.type,
            "modelId": model_id,
            "description": desired.description,
            "index": self.next_diagram_index(),
            "labels": desired_diagram_labels(desired, self.source),
        }
        if self.client.dry_run:
            fake_id = f"dry-diagram-{desired.key}"
            self.diagram_key_to_id[desired.key] = fake_id
            self.changes.append(f"CREATE diagram {desired.name}")
            return
        response = self.client.post(
            f"/landscapes/{self.source.landscape_id}/versions/{self.source.version_id}/diagrams",
            payload,
        )
        created = response["diagram"]
        self.diagrams.append(created)
        self.diagram_key_to_id[desired.key] = created["id"]
        self.changes.append(f"CREATED diagram {created['id']} {created.get('name')}")

    def next_diagram_index(self) -> int:
        if not self.diagrams:
            return 0
        return int(max(diagram.get("index", 0) for diagram in self.diagrams) + 1)

    def replace_diagram(self, updated: dict[str, Any]) -> None:
        self.diagrams = [
            updated if diagram["id"] == updated["id"] else diagram for diagram in self.diagrams
        ]

    @staticmethod
    def desired_diagram_name(existing: dict[str, Any], desired: DiagramSpec) -> str:
        if (
            desired.key == "runtime"
            and existing.get("name") == "Deployed DLH-in-a-box Runtime App Diagram"
        ):
            return existing["name"]
        return desired.name

    def sync_diagram_content(self) -> None:
        for key, diagram in self.source.diagrams.items():
            diagram_id = self.diagram_key_to_id[key]
            existing_content = self.fetch_diagram_content(diagram_id)
            desired_content = self.build_diagram_content(diagram, existing_content)
            if self.content_equivalent(existing_content, desired_content):
                continue
            if self.client.dry_run:
                self.changes.append(f"UPDATE diagram content {diagram.name}")
                continue
            self.client.put(
                f"/landscapes/{self.source.landscape_id}/versions/{self.source.version_id}/diagrams/{diagram_id}/content",
                desired_content,
            )
            self.changes.append(f"UPDATED diagram content {diagram.name}")

    def fetch_diagram_content(self, diagram_id: str) -> dict[str, Any]:
        if self.client.dry_run and diagram_id.startswith("dry-diagram-"):
            return {"objects": {}, "connections": {}, "comments": {}}
        payload = self.client.get(
            f"/landscapes/{self.source.landscape_id}/versions/{self.source.version_id}/diagrams/{diagram_id}/content"
        )
        return payload.get("diagramContent", {"objects": {}, "connections": {}, "comments": {}})

    def build_diagram_content(
        self,
        diagram: DiagramSpec,
        existing_content: dict[str, Any],
    ) -> dict[str, Any]:
        existing_objects = existing_content.get("objects") or {}
        existing_connections = existing_content.get("connections") or {}
        object_by_model_id = {
            item.get("modelId"): item
            for item in existing_objects.values()
            if item.get("modelId")
        }

        canvas_objects: dict[str, dict[str, Any]] = {}
        object_canvas_id_by_source: dict[str, str] = {}

        if diagram.type != "context-diagram":
            model_id = self.source_to_object_id[diagram.model_source_id]
            area = self.parent_area_object(diagram, model_id)
            canvas_objects[area["id"]] = area

        for index, source_id in enumerate(diagram.object_source_ids):
            model_id = self.source_to_object_id[source_id]
            source_obj = self.source.objects[source_id]
            existing = object_by_model_id.get(model_id)
            position = self.position_for(diagram.key, source_id, index)
            if existing:
                diagram_obj = dict(existing)
                diagram_obj.update(
                    {
                        "modelId": model_id,
                        "type": source_obj.type,
                        "shape": "area" if source_obj.type == "group" else "box",
                    }
                )
                if self.update_layout:
                    if source_obj.type == "group":
                        position = self.group_position_for(diagram.key, source_id, position)
                    diagram_obj.update(position)
            else:
                diagram_obj = {
                    "id": stable_canvas_id(diagram.key, "object", model_id),
                    "modelId": model_id,
                    "shape": "area" if source_obj.type == "group" else "box",
                    "type": source_obj.type,
                    "x": position["x"],
                    "y": position["y"],
                    "width": position["width"],
                    "height": position["height"],
                }
            if source_obj.type == "group" and not existing:
                group_position = self.group_position_for(diagram.key, source_id, position)
                diagram_obj.update(group_position)
                diagram_obj["shape"] = "area"
                diagram_obj["type"] = "group"
            canvas_objects[diagram_obj["id"]] = diagram_obj
            object_canvas_id_by_source[source_id] = diagram_obj["id"]

        connection_by_model_id = {
            item.get("modelId"): item
            for item in existing_connections.values()
            if item.get("modelId")
        }
        canvas_connections: dict[str, dict[str, Any]] = {}
        for source_id in diagram.connection_source_ids:
            connection = self.source.connections[source_id]
            if (
                connection.origin_source_id not in object_canvas_id_by_source
                or connection.target_source_id not in object_canvas_id_by_source
            ):
                continue
            model_id = self.source_to_connection_id[source_id]
            origin_canvas_id = object_canvas_id_by_source[connection.origin_source_id]
            target_canvas_id = object_canvas_id_by_source[connection.target_source_id]
            origin_obj = canvas_objects[origin_canvas_id]
            target_obj = canvas_objects[target_canvas_id]
            existing = None if self.update_layout else connection_by_model_id.get(model_id)
            diagram_connection = self.connection_layout(
                diagram.key,
                model_id,
                origin_canvas_id,
                target_canvas_id,
                origin_obj,
                target_obj,
                existing,
            )
            canvas_connections[diagram_connection["id"]] = diagram_connection

        content = {
            "objects": canvas_objects,
            "connections": canvas_connections,
            "comments": existing_content.get("comments") or {},
        }
        return content

    def parent_area_object(self, diagram: DiagramSpec, model_id: str) -> dict[str, Any]:
        bounds = self.diagram_bounds(diagram.key)
        source_obj = self.source.objects.get(diagram.model_source_id)
        object_type = source_obj.type if source_obj else "system"
        return {
            "id": stable_canvas_id(diagram.key, "parent", model_id),
            "modelId": model_id,
            "shape": "area",
            "type": object_type,
            "x": bounds["x"],
            "y": bounds["y"],
            "width": bounds["width"],
            "height": bounds["height"],
        }

    def diagram_bounds(self, diagram_key: str) -> dict[str, int]:
        diagram = self.source.diagrams.get(diagram_key)
        if diagram and diagram.bounds:
            return diagram.bounds
        return DIAGRAM_BOUNDS.get(diagram_key, DEFAULT_DIAGRAM_BOUNDS)

    def position_for(self, diagram_key: str, source_id: str, index: int) -> dict[str, int]:
        source_obj = self.source.objects.get(source_id)
        if source_obj and source_obj.layout.get(diagram_key):
            return source_obj.layout[diagram_key]
        explicit = EXPLICIT_POSITIONS.get(diagram_key, {}).get(source_id)
        if explicit:
            return explicit
        column = index % 4
        row = index // 4
        return {
            "x": 80 + column * 360,
            "y": 80 + row * 190,
            "width": 256,
            "height": 128,
        }

    def group_position_for(
        self,
        diagram_key: str,
        source_id: str,
        fallback: dict[str, int],
    ) -> dict[str, int]:
        source_obj = self.source.objects.get(source_id)
        if source_obj and source_obj.layout.get(diagram_key):
            return source_obj.layout[diagram_key]
        return EXPLICIT_GROUP_POSITIONS.get(diagram_key, {}).get(source_id, fallback)

    def connection_layout(
        self,
        diagram_key: str,
        model_id: str,
        origin_canvas_id: str,
        target_canvas_id: str,
        origin_obj: dict[str, Any],
        target_obj: dict[str, Any],
        existing: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if existing:
            diagram_connection = dict(existing)
            diagram_connection.update(
                {
                    "modelId": model_id,
                    "originId": origin_canvas_id,
                    "targetId": target_canvas_id,
                }
            )
            return diagram_connection

        origin_connector, target_connector, points = connector_points(origin_obj, target_obj)
        return {
            "id": stable_canvas_id(diagram_key, "connection", model_id),
            "modelId": model_id,
            "originId": origin_canvas_id,
            "targetId": target_canvas_id,
            "originConnector": origin_connector,
            "targetConnector": target_connector,
            "points": points,
            "lineShape": "curved",
            "labelPosition": 50,
        }

    @staticmethod
    def content_equivalent(existing: dict[str, Any], desired: dict[str, Any]) -> bool:
        def without_commit(content: dict[str, Any]) -> dict[str, Any]:
            return {
                "objects": content.get("objects") or {},
                "connections": content.get("connections") or {},
                "comments": content.get("comments") or {},
            }

        return without_commit(existing) == without_commit(desired)

    def verify(self) -> list[str]:
        missing: list[str] = []
        actual_object_ids = {obj["id"] for obj in self.objects}
        for source_id, actual_id in self.source_to_object_id.items():
            if source_id == ROOT_PARENT:
                continue
            if actual_id not in actual_object_ids and not actual_id.startswith("dry-object-"):
                missing.append(f"object {source_id}")
        actual_connection_ids = {connection["id"] for connection in self.connections}
        for source_id, actual_id in self.source_to_connection_id.items():
            if actual_id not in actual_connection_ids and not actual_id.startswith("dry-connection-"):
                missing.append(f"connection {source_id}")
        return missing


def stable_canvas_id(*parts: str) -> str:
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:11]
    return f"i{digest}"


def object_center(obj: dict[str, Any]) -> tuple[float, float]:
    return (float(obj["x"]) + float(obj["width"]) / 2, float(obj["y"]) + float(obj["height"]) / 2)


def connector_points(
    origin_obj: dict[str, Any],
    target_obj: dict[str, Any],
) -> tuple[str, str, list[dict[str, float]]]:
    ox, oy = object_center(origin_obj)
    tx, ty = object_center(target_obj)
    if abs(tx - ox) >= abs(ty - oy):
        if tx >= ox:
            origin_connector = "right-middle"
            target_connector = "left-middle"
            start = {"x": origin_obj["x"] + origin_obj["width"], "y": oy}
            end = {"x": target_obj["x"], "y": ty}
        else:
            origin_connector = "left-middle"
            target_connector = "right-middle"
            start = {"x": origin_obj["x"], "y": oy}
            end = {"x": target_obj["x"] + target_obj["width"], "y": ty}
    else:
        if ty >= oy:
            origin_connector = "bottom-center"
            target_connector = "top-center"
            start = {"x": ox, "y": origin_obj["y"] + origin_obj["height"]}
            end = {"x": tx, "y": target_obj["y"]}
        else:
            origin_connector = "top-center"
            target_connector = "bottom-center"
            start = {"x": ox, "y": origin_obj["y"]}
            end = {"x": tx, "y": target_obj["y"] + target_obj["height"]}
    return origin_connector, target_connector, [start, end]


def pos(x: int, y: int, width: int = 256, height: int = 128) -> dict[str, int]:
    return {"x": x, "y": y, "width": width, "height": height}


EXPLICIT_POSITIONS: dict[str, dict[str, dict[str, int]]] = {
    "context": {
        "DLH-L1-OPERATOR": pos(80, -180, height=160),
        "DLH-L1-CONSUMER-REPO": pos(420, -120),
        "DLH-L1-UPSTREAM-DEPS": pos(420, 140),
        "DLH-L1-CHART": pos(780, 20),
        "DLH-L1-RUNTIME": pos(1160, 20),
        "DLH-L1-TARGET-CLUSTER": pos(1160, 260),
        "DLH-L1-USER": pos(1520, -80, height=160),
    },
    "chart-product": {
        "DLH-X-SUPERSET-CHART": pos(-280, -240),
        "DLH-X-PREFECT-SERVER-CHART": pos(-280, -100),
        "DLH-X-PREFECT-WORKER-CHART": pos(-280, 40),
        "DLH-X-OAUTH2-PROXY-CHART": pos(-280, 180),
        "DLH-X-KEYCLOAK-CHART": pos(-280, 320),
        "DLH-X-SPARK-OPERATOR-CHART": pos(20, -240),
        "DLH-X-MINIO-CHART": pos(20, -100),
        "DLH-X-DATAHUB-CHART": pos(20, 40),
        "DLH-X-DATAHUB-PREREQS-CHART": pos(20, 180),
        "DLH-X-VAULT-CHART": pos(20, 320),
        "DLH-X-JUPYTERHUB-CHART": pos(320, -240),
        "DLH-X-POSTGRESQL-CHART": pos(320, -100),
        "DLH-X-TRINO-CHART": pos(320, 40),
        "DLH-X-HIVE-IMAGE": pos(320, 180),
        "DLH-C2-UPSTREAM-ARCHIVES": pos(680, -240),
        "DLH-C2-CHART-SOURCE": pos(680, -40),
        "DLH-C2-TRINO-VENDORED": pos(680, 160),
        "DLH-C2-HIVE-SUBCHART": pos(680, 340),
        "DLH-C2-EXAMPLE-PROFILES": pos(1060, -220),
        "DLH-C2-VALIDATION": pos(1060, 20),
        "DLH-C2-PUBLISH": pos(1400, 20),
        "DLH-C2-OCI-PACKAGE": pos(1780, -120),
        "DLH-X-CONSUMER-REPO": pos(1780, 140),
    },
    "runtime": {
        "DLH-X-USERS": pos(60, -900, height=160),
        "DLH-X-INGRESS-CONTROLLER": pos(440, -860),
        "DLH-X-OIDC": pos(900, -860),
        "DLH-X-LDAP": pos(-300, -260),
        "DLH-X-SECRET-SYNC": pos(-320, 220),
        "DLH-X-OBJECT-STORAGE": pos(80, 780),
        "DLH-X-SOURCE-SYSTEMS": pos(1960, 760),
        "DLH-X-PIPELINE-CODE": pos(1960, 560),
        "DLH-R-PLATFORM-HOME": pos(80, -580),
        "DLH-R-AUTH-PROXIES": pos(420, -580),
        "DLH-R-KEYCLOAK": pos(280, -240),
        "DLH-R-KEYCLOAK-DB": pos(680, -240),
        "DLH-R-VAULT": pos(80, 120),
        "DLH-R-RANGER": pos(780, 80),
        "DLH-R-RANGER-DB": pos(1180, 80),
        "DLH-R-TRINO": pos(780, 360),
        "DLH-R-HIVE": pos(380, 360),
        "DLH-R-HIVE-DB": pos(380, 560),
        "DLH-R-MINIO": pos(780, 620),
        "DLH-R-SUPERSET": pos(1180, -620),
        "DLH-R-SUPERSET-DB": pos(1560, -720),
        "DLH-R-SUPERSET-REDIS": pos(1560, -540),
        "DLH-R-JUPYTERHUB": pos(1180, -360),
        "DLH-R-JUPYTER-PODS": pos(1560, -360),
        "DLH-R-CLOUDBEAVER": pos(1180, -120),
        "DLH-R-PREFECT-SERVER": pos(1180, 520),
        "DLH-R-PREFECT-DB": pos(1560, 520),
        "DLH-R-PREFECT-WORKER": pos(1180, 740),
        "DLH-R-SPARK-OPERATOR": pos(780, 840),
        "DLH-R-DATAHUB": pos(1180, 220),
        "DLH-R-DATAHUB-MYSQL": pos(1560, 40),
        "DLH-R-DATAHUB-KAFKA": pos(1560, 220),
        "DLH-R-DATAHUB-ELASTICSEARCH": pos(1560, 400),
    },
}

EXPLICIT_GROUP_POSITIONS: dict[str, dict[str, dict[str, int]]] = {
    "chart-product": {
        "DLH-G-chart-product-UPSTREAM-SOURCES": pos(-340, -300, 900, 800),
        "DLH-G-chart-product-CHART-SOURCE": pos(620, -300, 560, 800),
        "DLH-G-chart-product-INSTALL-PROFILES": pos(1020, -300, 340, 220),
        "DLH-G-chart-product-AUTOMATION": pos(1020, -60, 720, 260),
        "DLH-G-chart-product-PUBLISHED-ARTIFACT": pos(1740, -220, 360, 500),
    },
    "runtime": {
        "DLH-G-runtime-BROWSER-ENTRY": pos(20, -660, 720, 240),
        "DLH-G-runtime-IDENTITY-AND-SECRETS": pos(-360, -360, 1380, 660),
        "DLH-G-runtime-GOVERNANCE": pos(720, -20, 760, 260),
        "DLH-G-runtime-LAKEHOUSE-CORE": pos(320, 300, 820, 520),
        "DLH-G-runtime-ANALYSIS-TOOLS": pos(1120, -780, 760, 560),
        "DLH-G-runtime-ORCHESTRATION-AND-COMPUTE": pos(720, 460, 1180, 460),
        "DLH-G-runtime-DISCOVERY": pos(1120, 120, 760, 360),
        "DLH-G-runtime-SUPPORT-SERVICES-AND-STORES": pos(1500, -780, 380, 1380),
    },
}


def print_summary(runner: SyncRunner, source: SourceModel, dry_run: bool) -> None:
    mode = "DRY-RUN" if dry_run else "APPLIED"
    print(f"{mode}: {len(source.objects)} source objects, {len(source.connections)} source connections, {len(source.diagrams)} diagrams")
    if runner.changes:
        print(f"{len(runner.changes)} planned/applied changes:")
        for change in runner.changes:
            print(f"- {change}")
    else:
        print("No changes required.")
    missing = runner.verify()
    if missing:
        print("Verification gaps:")
        for item in missing:
            print(f"- {item}")
        if not dry_run:
            raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write changes to IcePanel")
    parser.add_argument(
        "--source",
        default=DEFAULT_JSON_SOURCE_FILE,
        help="Source model path, relative to the repository root",
    )
    parser.add_argument(
        "--source-format",
        choices=["auto", "json", "markdown"],
        default="auto",
        help="Source model format. Defaults to extension-based detection.",
    )
    parser.add_argument(
        "--write-json",
        help=(
            "Write the parsed source model as canonical JSON and exit. "
            "Use with --source-format markdown for the transition import path."
        ),
    )
    parser.add_argument(
        "--update-layout",
        action="store_true",
        help="Reset official diagram object positions from the source model layout.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    source_path = Path(args.source)
    if not source_path.is_absolute():
        source_path = repo_root / source_path
    if not source_path.exists():
        raise RuntimeError(f"Source model not found: {source_path}")

    source = load_source_model(source_path, args.source_format)
    if args.write_json:
        output_path = Path(args.write_json)
        if not output_path.is_absolute():
            output_path = repo_root / output_path
        write_json_source_model(source, output_path, relative_path(output_path))
        print(f"Wrote canonical JSON model: {output_path}")
        return 0

    api_key = load_api_key(repo_root)
    client = IcePanelClient(api_key, dry_run=not args.apply)
    runner = SyncRunner(repo_root, client, source, update_layout=args.update_layout)
    runner.run()
    print_summary(runner, source, dry_run=not args.apply)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
