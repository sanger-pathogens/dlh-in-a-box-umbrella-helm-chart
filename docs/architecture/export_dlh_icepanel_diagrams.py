#!/usr/bin/env python3
"""Export official DLH-in-a-box IcePanel diagrams as PNG files."""

from __future__ import annotations

import argparse
import time
import urllib.request
from pathlib import Path
from typing import Any

from sync_dlh_icepanel import (
    DEFAULT_JSON_SOURCE_FILE,
    IcePanelClient,
    list_response,
    load_api_key,
    load_source_model,
)


DEFAULT_OUTPUT_DIR = "docs/architecture/icepanel/exports/dlh-in-a-box/png-dark"


def wait_for_export(
    client: IcePanelClient,
    source: Any,
    diagram_id: str,
    export_id: str,
    *,
    timeout_seconds: int,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    current: dict[str, Any] = {}
    while time.monotonic() < deadline:
        payload = client.get(
            f"/landscapes/{source.landscape_id}/versions/{source.version_id}"
            f"/diagrams/{diagram_id}/export/image/{export_id}"
        )
        current = payload["diagramExportImage"]
        if current.get("error"):
            raise RuntimeError(f"IcePanel export failed: {current['error']}")
        if current.get("completedAt") and (current.get("fileUrls") or {}).get("png"):
            return current
        time.sleep(2)
    raise TimeoutError(f"Timed out waiting for IcePanel export {export_id}")


def download_png(url: str, output_path: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError(f"Downloaded file is not a PNG: {output_path}")
    output_path.write_bytes(data)


def export_diagrams(
    *,
    repo_root: Path,
    source_path: Path,
    output_dir: Path,
    theme: str,
    max_width: int,
    dry_run: bool,
) -> list[Path]:
    source = load_source_model(source_path, "json")
    client = IcePanelClient(load_api_key(repo_root), dry_run=False)
    diagrams = list_response(
        client.get(f"/landscapes/{source.landscape_id}/versions/{source.version_id}/diagrams"),
        "diagrams",
    )
    diagram_label = source.labels["diagramKey"]
    live_by_key = {
        diagram.get("labels", {}).get(diagram_label): diagram
        for diagram in diagrams
        if diagram.get("labels", {}).get(diagram_label)
    }

    missing = [key for key in source.diagrams if key not in live_by_key]
    if missing:
        raise RuntimeError(f"Missing official IcePanel diagrams: {', '.join(missing)}")

    exported: list[Path] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    for key, diagram_spec in source.diagrams.items():
        live_diagram = live_by_key[key]
        output_path = output_dir / diagram_spec.export_filename
        if dry_run:
            print(f"Would export {key} -> {output_path}")
            exported.append(output_path)
            continue
        payload = client.post(
            f"/landscapes/{source.landscape_id}/versions/{source.version_id}"
            f"/diagrams/{live_diagram['id']}/export/image",
            {"theme": theme, "maxWidth": max_width},
        )
        export = payload["diagramExportImage"]
        export = wait_for_export(
            client,
            source,
            live_diagram["id"],
            export["id"],
            timeout_seconds=120,
        )
        download_png(export["fileUrls"]["png"], output_path)
        print(f"Exported {key}: {output_path}")
        exported.append(output_path)
    return exported


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=DEFAULT_JSON_SOURCE_FILE)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--theme", choices=["dark", "light"], default="dark")
    parser.add_argument("--max-width", type=int, default=1800)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    source_path = Path(args.source)
    if not source_path.is_absolute():
        source_path = repo_root / source_path
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir

    exported = export_diagrams(
        repo_root=repo_root,
        source_path=source_path,
        output_dir=output_dir,
        theme=args.theme,
        max_width=args.max_width,
        dry_run=args.dry_run,
    )
    print(f"{'Checked' if args.dry_run else 'Exported'} {len(exported)} diagrams")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
