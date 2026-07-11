#!/usr/bin/env python3
"""Statically validate the three-platform Executa release workflow."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "release.yml"
EXPECTED_MATRIX = {
    (
        "macos-15",
        "darwin-arm64",
        "tar.gz",
    ),
    (
        "macos-15-intel",
        "darwin-x86_64",
        "tar.gz",
    ),
    (
        "windows-latest",
        "windows-x86_64",
        "zip",
    ),
}
EXPECTED_ASSETS = {
    "mini-notes-summary-darwin-arm64.tar.gz",
    "mini-notes-summary-darwin-x86_64.tar.gz",
    "mini-notes-summary-windows-x86_64.zip",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def as_mapping(value: Any, name: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{name} must be a mapping")
    return value


def main() -> int:
    workflow_value = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    workflow = as_mapping(workflow_value, "workflow")

    triggers_value = workflow.get("on", workflow.get(True))
    triggers = as_mapping(triggers_value, "on")
    require("workflow_dispatch" in triggers, "workflow_dispatch trigger is missing")
    dispatch = as_mapping(triggers.get("workflow_dispatch"), "on.workflow_dispatch")
    inputs = as_mapping(dispatch.get("inputs"), "on.workflow_dispatch.inputs")
    release_tag = as_mapping(inputs.get("release_tag"), "release_tag input")
    require(release_tag.get("required") is True, "release_tag input must be required")
    push = as_mapping(triggers.get("push"), "on.push")
    tags = push.get("tags")
    require(isinstance(tags, list) and "v*" in tags, "push tag trigger v* is missing")

    permissions = as_mapping(workflow.get("permissions"), "permissions")
    require(permissions.get("contents") == "write", "permissions.contents must be write")

    jobs = as_mapping(workflow.get("jobs"), "jobs")
    validate_app = as_mapping(jobs.get("validate-app"), "jobs.validate-app")
    require(
        validate_app.get("runs-on") == "ubuntu-latest",
        "validate-app must run on ubuntu-latest",
    )
    validate_text = json.dumps(validate_app, ensure_ascii=False)
    for required in (
        "actions/checkout@v4",
        "actions/setup-node@v4",
        '"node-version": "22"',
        "astral-sh/setup-uv@v6",
        '"python-version": "3.12"',
        "npm ci",
        "npm run build",
        "npm run validate",
        "npm run check:identity",
        "npm run check:no-direct-llm",
        "npm run test:protocol",
        "npm run executa:mock",
    ):
        require(required in validate_text, f"validate-app is missing {required}")

    build = as_mapping(jobs.get("build"), "jobs.build")
    build_needs = build.get("needs")
    require(
        build_needs == "validate-app"
        or (isinstance(build_needs, list) and "validate-app" in build_needs),
        "build job must need validate-app",
    )
    strategy = as_mapping(build.get("strategy"), "jobs.build.strategy")
    matrix = as_mapping(strategy.get("matrix"), "jobs.build.strategy.matrix")
    include = matrix.get("include")
    require(isinstance(include, list), "build matrix.include must be a list")
    actual_matrix = {
        (item.get("os"), item.get("platform"), item.get("archive_ext"))
        for item in include
        if isinstance(item, dict)
    }
    require(actual_matrix == EXPECTED_MATRIX, f"workflow matrix mismatch: {actual_matrix}")

    for item in include:
        require(isinstance(item, dict), "every matrix entry must be a mapping")
        platform_key = item.get("platform")
        archive_ext = item.get("archive_ext")
        if str(platform_key).startswith("darwin-"):
            require(archive_ext == "tar.gz", "macOS archive must use tar.gz")
        if platform_key == "windows-x86_64":
            require(archive_ext == "zip", "Windows archive must use zip")

    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    require("macos-13" not in workflow_text, "deprecated macos-13 runner is forbidden")
    require("macos-14" not in workflow_text, "deprecated macos-14 runner is forbidden")

    build_text = json.dumps(build, ensure_ascii=False)
    for required in (
        "test:executa",
        "check:identity",
        "build_binary.py",
        "smoke_binary.py",
        "verify_archive.py",
        "actions/upload-artifact@v4",
    ):
        require(required in build_text, f"build job is missing {required}")

    release = as_mapping(jobs.get("release"), "jobs.release")
    require(release.get("needs") == "build", "release job must need build")
    release_text = json.dumps(release, ensure_ascii=False)
    require(
        "actions/download-artifact@v4" in release_text,
        "release job must download workflow artifacts",
    )
    require(
        "softprops/action-gh-release@v2" in release_text,
        "release job must upload GitHub Release assets",
    )
    for asset in EXPECTED_ASSETS:
        require(asset in release_text, f"release job is missing asset {asset}")
    require(
        "workflow_dispatch may only publish a prerelease tag" in release_text,
        "manual runs must be prevented from overwriting a formal release tag",
    )
    require(
        "workflow_dispatch requires release_tag" in release_text,
        "manual release_tag must be checked before release creation",
    )

    print(
        "Workflow static validation passed: validate-app (Node 22, Python 3.12, "
        "npm ci, App build/strict validation, identity, no-direct-LLM, protocol, "
        "mock Sampling); 3 native runners/platform keys; contents:write; native "
        "smoke; archive verify; artifact aggregation; GitHub Release upload"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, yaml.YAMLError) as error:
        print(f"check_workflow.py: {error}", file=sys.stderr)
        raise SystemExit(1) from error
