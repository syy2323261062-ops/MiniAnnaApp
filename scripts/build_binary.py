#!/usr/bin/env python3
"""Build the native Executa and package its platform archive."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_DIR = REPO_ROOT / "executas" / "mini-notes-summary-python"
SPEC_PATH = PROJECT_DIR / "pyinstaller.spec"
MANIFEST_TEMPLATE = PROJECT_DIR / "packaging" / "manifest.template.json"
DIST_ROOT = REPO_ROOT / "dist"
RELEASE_DIR = DIST_ROOT / "release"
BUILD_ROOT = DIST_ROOT / "pyinstaller" / "build"
OUTPUT_ROOT = DIST_ROOT / "pyinstaller" / "output"
STAGING_ROOT = DIST_ROOT / "staging"

ARCHIVE_NAMES = {
    "darwin-arm64": "mini-notes-summary-darwin-arm64.tar.gz",
    "darwin-x86_64": "mini-notes-summary-darwin-x86_64.tar.gz",
    "windows-x86_64": "mini-notes-summary-windows-x86_64.zip",
}


def host_platform_key() -> str:
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
    raise RuntimeError(
        f"unsupported build host: system={platform.system()!r}, "
        f"machine={platform.machine()!r}"
    )


def remove_owned_directory(path: Path) -> None:
    resolved = path.resolve()
    dist_resolved = DIST_ROOT.resolve()
    if resolved == dist_resolved or dist_resolved not in resolved.parents:
        raise RuntimeError(f"refusing to remove path outside dist/: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def executable_name(platform_key: str) -> str:
    return (
        "mini-notes-summary.exe"
        if platform_key == "windows-x86_64"
        else "mini-notes-summary"
    )


def run_pyinstaller(platform_key: str, build_dir: Path, output_dir: Path) -> Path:
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required on PATH to install and run PyInstaller")

    command = [
        uv,
        "run",
        "--python",
        "3.12",
        "--project",
        str(PROJECT_DIR),
        "--extra",
        "build",
        "python",
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--workpath",
        str(build_dir),
        "--distpath",
        str(output_dir),
        str(SPEC_PATH),
    ]
    print(f"Building {platform_key} with PyInstaller spec: {SPEC_PATH}")
    subprocess.run(command, cwd=REPO_ROOT, check=True)

    result = output_dir / executable_name(platform_key)
    if not result.is_file():
        raise RuntimeError(f"PyInstaller did not create expected executable: {result}")
    return result


def stage_files(platform_key: str, built_binary: Path, staging_dir: Path) -> Path:
    manifest = json.loads(MANIFEST_TEMPLATE.read_text(encoding="utf-8"))
    if manifest.get("name") != "mini-notes-summary":
        raise RuntimeError("binary manifest name drifted from mini-notes-summary")
    if manifest.get("version") != "0.1.0":
        raise RuntimeError("binary manifest version drifted from 0.1.0")

    bin_dir = staging_dir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MANIFEST_TEMPLATE, staging_dir / "manifest.json")
    staged_binary = bin_dir / executable_name(platform_key)
    shutil.copy2(built_binary, staged_binary)
    if platform_key.startswith("darwin-"):
        staged_binary.chmod(0o755)
    return staged_binary


def create_archive(platform_key: str, staging_dir: Path) -> Path:
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    archive = RELEASE_DIR / ARCHIVE_NAMES[platform_key]
    if archive.exists():
        archive.unlink()

    binary_rel = Path("bin") / executable_name(platform_key)
    if platform_key == "windows-x86_64":
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.write(staging_dir / "manifest.json", "manifest.json")
            bundle.write(staging_dir / binary_rel, binary_rel.as_posix())
    else:
        with tarfile.open(archive, "w:gz") as bundle:
            bundle.add(staging_dir / "manifest.json", arcname="manifest.json")
            bundle.add(staging_dir / binary_rel, arcname=binary_rel.as_posix())
    return archive


def verify_archive(archive: Path) -> None:
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "verify_archive.py"), str(archive)],
        cwd=REPO_ROOT,
        check=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--platform",
        choices=sorted(ARCHIVE_NAMES),
        help="platform to build; must match the current host",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError(
            f"Python 3.12 is required; running {platform.python_version()}"
        )

    detected = host_platform_key()
    requested = args.platform or detected
    if requested != detected:
        raise RuntimeError(
            f"cross-build refused: requested {requested}, current host is {detected}"
        )

    build_dir = BUILD_ROOT / requested
    output_dir = OUTPUT_ROOT / requested
    staging_dir = STAGING_ROOT / requested
    for path in (build_dir, output_dir, staging_dir):
        remove_owned_directory(path)
        path.mkdir(parents=True, exist_ok=True)

    built_binary = run_pyinstaller(requested, build_dir, output_dir)
    staged_binary = stage_files(requested, built_binary, staging_dir)
    archive = create_archive(requested, staging_dir)
    verify_archive(archive)

    print(f"Executable: {staged_binary}")
    print(f"Archive: {archive}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"build_binary.py: {error}", file=sys.stderr)
        raise SystemExit(1) from error
