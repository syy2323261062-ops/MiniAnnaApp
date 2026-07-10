#!/usr/bin/env python3
"""Strictly verify a Mini Notes Summary binary distribution archive."""

from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


ARCHIVE_PATTERN = re.compile(
    r"^mini-notes-summary-"
    r"(?P<platform>darwin-arm64|darwin-x86_64|windows-x86_64)"
    r"(?P<extension>\.tar\.gz|\.zip)$"
)
EXPECTED_EXTENSIONS = {
    "darwin-arm64": ".tar.gz",
    "darwin-x86_64": ".tar.gz",
    "windows-x86_64": ".zip",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def platform_from_filename(archive: Path) -> str:
    match = ARCHIVE_PATTERN.fullmatch(archive.name)
    if match is None:
        raise RuntimeError(
            "archive filename must be exactly one supported release asset name"
        )
    platform_key = match.group("platform")
    require(
        match.group("extension") == EXPECTED_EXTENSIONS[platform_key],
        f"wrong archive extension for {platform_key}",
    )
    return platform_key


def validate_member_path(name: str) -> str:
    require(bool(name), "archive contains an empty path")
    require("\\" not in name, f"archive path uses backslashes: {name!r}")
    path = PurePosixPath(name)
    require(not path.is_absolute(), f"archive contains absolute path: {name!r}")
    require(".." not in path.parts, f"archive contains path traversal: {name!r}")
    require(
        not path.parts or ":" not in path.parts[0],
        f"archive contains drive-qualified path: {name!r}",
    )
    normalized = path.as_posix()
    require(normalized not in {".", ""}, f"invalid archive path: {name!r}")
    return normalized


def read_archive(archive: Path) -> tuple[list[str], dict[str, bytes]]:
    names: list[str] = []
    files: dict[str, bytes] = {}
    if archive.name.endswith(".zip"):
        require(zipfile.is_zipfile(archive), "archive is not a valid zip file")
        with zipfile.ZipFile(archive) as bundle:
            for info in bundle.infolist():
                name = validate_member_path(info.filename)
                require(name not in names, f"duplicate archive path: {name}")
                names.append(name)
                if not info.is_dir():
                    files[name] = bundle.read(info)
    else:
        require(tarfile.is_tarfile(archive), "archive is not a valid tar archive")
        with tarfile.open(archive, "r:gz") as bundle:
            for member in bundle.getmembers():
                name = validate_member_path(member.name)
                require(name not in names, f"duplicate archive path: {name}")
                names.append(name)
                require(
                    member.isfile() or member.isdir(),
                    f"archive contains unsupported link or special file: {name}",
                )
                if member.isfile():
                    stream = bundle.extractfile(member)
                    require(stream is not None, f"could not read archive member: {name}")
                    files[name] = stream.read()
    return names, files


def resolve_entrypoint(manifest: dict[str, Any], platform_key: str) -> str:
    runtime = manifest.get("runtime")
    require(isinstance(runtime, dict), "manifest.runtime must be an object")
    binary = runtime.get("binary")
    require(isinstance(binary, dict), "manifest.runtime.binary must be an object")
    entrypoint = binary.get("entrypoint")
    if isinstance(entrypoint, str):
        selected = entrypoint
    elif isinstance(entrypoint, dict):
        os_key = platform_key.split("-", maxsplit=1)[0]
        selected = (
            entrypoint.get(platform_key)
            or entrypoint.get(os_key)
            or entrypoint.get("default")
        )
    else:
        raise RuntimeError("manifest runtime.binary.entrypoint must be a string or map")
    require(isinstance(selected, str) and bool(selected), "no entrypoint for platform")
    return validate_member_path(selected)


def detect_host_platform() -> str | None:
    system = platform.system().lower()
    machine = platform.machine().lower()
    architecture = {
        "amd64": "x86_64",
        "x86_64": "x86_64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }.get(machine)
    if system == "windows" and architecture == "x86_64":
        return "windows-x86_64"
    if system == "darwin" and architecture in {"arm64", "x86_64"}:
        return f"darwin-{architecture}"
    return None


def verify_archive(archive: Path) -> tuple[str, list[str], str]:
    archive = archive.resolve()
    require(archive.is_file(), f"archive does not exist: {archive}")
    require(archive.stat().st_size > 0, "archive is empty")
    platform_key = platform_from_filename(archive)
    names, files = read_archive(archive)
    require(bool(files), "archive contains no files")
    require("manifest.json" in files, "archive root is missing manifest.json")
    require(any(name.startswith("bin/") for name in files), "archive root is missing bin/")

    for name in names:
        top_level = PurePosixPath(name).parts[0]
        require(
            top_level in {"manifest.json", "bin"},
            f"archive has an extra top-level path or parent directory: {name}",
        )

    try:
        manifest_value = json.loads(files["manifest.json"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("archive manifest.json is not valid UTF-8 JSON") from error
    require(isinstance(manifest_value, dict), "archive manifest must be an object")
    manifest: dict[str, Any] = manifest_value
    require(manifest.get("name") == "mini-notes-summary", "manifest name mismatch")
    require(manifest.get("version") == "0.1.0", "manifest version mismatch")

    entrypoint = resolve_entrypoint(manifest, platform_key)
    require(entrypoint in files, f"manifest entrypoint is absent: {entrypoint}")
    if platform_key == "windows-x86_64":
        require(entrypoint.endswith(".exe"), "Windows entrypoint must end in .exe")
    else:
        require(not entrypoint.endswith(".exe"), "macOS entrypoint must not end in .exe")
        permissions = manifest["runtime"]["binary"].get("permissions")
        require(isinstance(permissions, dict), "macOS manifest permissions missing")
        require(
            permissions.get("bin/mini-notes-summary") == "0o755",
            "macOS executable permission must be declared as 0o755",
        )

    expected_files = {"manifest.json", entrypoint}
    require(
        set(files) == expected_files,
        f"archive contains unexpected files: {sorted(set(files) - expected_files)}",
    )

    with tempfile.TemporaryDirectory(prefix="mini-notes-archive-") as temp_dir:
        extraction_root = Path(temp_dir)
        for name, content in files.items():
            destination = extraction_root / PurePosixPath(name)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        extracted_binary = extraction_root / PurePosixPath(entrypoint)
        if platform_key.startswith("darwin-"):
            extracted_binary.chmod(0o755)

        if detect_host_platform() == platform_key:
            subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).with_name("smoke_binary.py")),
                    "--binary",
                    str(extracted_binary),
                ],
                check=True,
            )
            smoke_status = "passed on native host"
        else:
            smoke_status = "skipped (archive platform differs from host)"

    print(
        f"Archive verification passed: platform={platform_key}; "
        f"entrypoint={entrypoint}; smoke={smoke_status}"
    )
    return platform_key, names, entrypoint


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    verify_archive(args.archive)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"verify_archive.py: {error}", file=sys.stderr)
        raise SystemExit(1) from error
