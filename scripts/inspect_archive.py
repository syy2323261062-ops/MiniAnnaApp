#!/usr/bin/env python3
"""Print a read-only review report for an Executa binary archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from verify_archive import platform_from_filename, read_archive, resolve_entrypoint


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    archive = args.archive.resolve()
    if not archive.is_file():
        raise RuntimeError(f"archive does not exist: {archive}")

    platform_key = platform_from_filename(archive)
    names, files = read_archive(archive)
    if "manifest.json" not in files:
        raise RuntimeError("archive root is missing manifest.json")
    manifest = json.loads(files["manifest.json"].decode("utf-8"))
    if not isinstance(manifest, dict):
        raise RuntimeError("manifest.json must contain an object")
    entrypoint = resolve_entrypoint(manifest, platform_key)
    if entrypoint not in files:
        raise RuntimeError(f"entrypoint is absent: {entrypoint}")

    archive_bytes = archive.read_bytes()
    executable = files[entrypoint]
    print(f"Archive: {archive.name}")
    print(f"Platform: {platform_key}")
    print("Paths:")
    for name in names:
        print(f"  {name}")
    print("Manifest:")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"Entrypoint: {entrypoint}")
    print(f"Executable size: {len(executable)} bytes")
    print(f"Executable SHA-256: {sha256_bytes(executable)}")
    print(f"Archive size: {len(archive_bytes)} bytes")
    print(f"Archive SHA-256: {sha256_bytes(archive_bytes)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"inspect_archive.py: {error}", file=sys.stderr)
        raise SystemExit(1) from error
