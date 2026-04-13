#!/usr/bin/env python3
"""Validate Mermaid fenced code blocks by rendering them with mermaid-cli."""

from __future__ import annotations

import argparse
import fnmatch
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


FENCE_RE = re.compile(r"^```mermaid[^\n]*\n(.*?)^```[ \t]*$", re.MULTILINE | re.DOTALL)
DEFAULT_IMAGE = os.environ.get("MERMAID_CLI_IMAGE", "minlag/mermaid-cli:10.9.1")
STRICT_ENV_VALUES = {"1", "true", "yes", "on"}
DOCKER_PROBE_TIMEOUT_SECONDS = float(os.environ.get("MERMAID_DOCKER_PROBE_TIMEOUT_SECONDS", "5"))
MERMAID_RENDER_TIMEOUT_SECONDS = float(os.environ.get("MERMAID_RENDER_TIMEOUT_SECONDS", "30"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--include", action="append", default=[], required=True)
    parser.add_argument("--exclude", action="append", default=[])
    return parser.parse_args()


def should_exclude(path: str, excludes: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in excludes)


def collect_files(root: Path, includes: list[str], excludes: list[str]) -> list[Path]:
    files: set[Path] = set()
    for pattern in includes:
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            rel_path = path.relative_to(root).as_posix()
            if should_exclude(rel_path, excludes):
                continue
            files.add(path)
    return sorted(files)


def docker_available() -> bool:
    try:
        result = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=DOCKER_PROBE_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        return False
    except subprocess.TimeoutExpired:
        return False

    return result.returncode == 0


def strict_mode_enabled() -> bool:
    return os.environ.get("CI", "").lower() in STRICT_ENV_VALUES or os.environ.get(
        "MERMAID_STRICT", ""
    ).lower() in STRICT_ENV_VALUES


def validate_block(path: Path, block_index: int, block: str) -> str | None:
    with tempfile.TemporaryDirectory(prefix="mermaid-check-") as tmpdir:
        tmp_path = Path(tmpdir)
        input_path = tmp_path / "diagram.mmd"
        output_path = tmp_path / "diagram.svg"
        container_tmp_path = tmp_path / "container-tmp"
        input_path.write_text(block, encoding="utf-8")
        container_tmp_path.mkdir(exist_ok=True)

        try:
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-u",
                    f"{os.getuid()}:{os.getgid()}",
                    "-e",
                    "TMPDIR=/work/container-tmp",
                    "-v",
                    f"{tmpdir}:/work",
                    DEFAULT_IMAGE,
                    "-i",
                    "/work/diagram.mmd",
                    "-o",
                    "/work/diagram.svg",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=MERMAID_RENDER_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            return (
                f"{path} mermaid block {block_index}: render timed out after "
                f"{MERMAID_RENDER_TIMEOUT_SECONDS:g}s"
            )

        if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
            return None

        diagnostic = "\n".join(part.strip() for part in [result.stdout, result.stderr] if part.strip())
        return f"{path} mermaid block {block_index}: render failed\n{diagnostic}".rstrip()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()

    if not docker_available():
        if strict_mode_enabled():
            print(
                "Docker is required for Mermaid validation in CI or strict mode. "
                "Install Docker or set SKIP_MERMAID_CHECK=1 only if you are intentionally bypassing the check.",
                file=sys.stderr,
            )
            return 1

        print(
            "Skipping Mermaid validation because Docker is not available locally. "
            "Set MERMAID_STRICT=1 to require Mermaid rendering outside CI.",
            file=sys.stderr,
        )
        return 0

    files = collect_files(root, args.include, args.exclude)
    errors: list[str] = []

    for path in files:
        content = path.read_text(encoding="utf-8")
        blocks = FENCE_RE.findall(content)
        for index, block in enumerate(blocks, start=1):
            error = validate_block(path.relative_to(root), index, block)
            if error:
                errors.append(error)

    if errors:
        print("\n\n".join(errors), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
