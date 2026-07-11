#!/usr/bin/env python3
"""Check identity constants across the App, Executa, fixture, and tests."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

from check_no_direct_llm import find_direct_llm_calls


ROOT = Path(__file__).resolve().parents[1]
APP_SLUG = "mini-notes"
HANDLE = "mini-notes-summary"
BUNDLED_REFERENCE = "bundled:mini-notes-summary"
LOCAL_TOOL_ID = "tool-test-mini-notes-summary-12345678"
TOOL_METHOD = "summarize_notes"
STORAGE_KEY = "mini-notes:notes:v1"
VERSION = "0.1.0"


failures: List[str] = []


def fail(location: str, message: str) -> None:
    failures.append(f"{location}: {message}")


def read_json(relative: str) -> Dict[str, Any]:
    path = ROOT / relative
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:  # noqa: BLE001
        fail(relative, f"cannot read JSON: {error}")
        return {}
    if not isinstance(value, dict):
        fail(relative, "root must be an object")
        return {}
    return value


def literal_assignment(relative: str, name: str) -> Any:
    path = ROOT / relative
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if isinstance(node, ast.Assign):
                if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                    return ast.literal_eval(node.value)
    except Exception as error:  # noqa: BLE001
        fail(relative, f"cannot parse {name}: {error}")
        return None
    fail(relative, f"assignment {name} not found")
    return None


def expect_equal(location: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        fail(location, f"expected {expected!r}, got {actual!r}")


def expect_text(relative: str, pattern: str, description: str) -> str:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    if re.search(pattern, text, flags=re.MULTILINE) is None:
        fail(relative, f"missing {description}")
    return text


def check_json_contracts() -> None:
    app = read_json("app.json")
    expect_equal("app.json:slug", app.get("slug"), APP_SLUG)
    expect_equal("app.json:version", app.get("version"), VERSION)
    bundled = app.get("bundled_executas", {})
    if not isinstance(bundled, dict) or HANDLE not in bundled:
        fail("app.json:bundled_executas", f"missing handle {HANDLE!r}")

    manifest = read_json("manifest.json")
    required = manifest.get("required_executas", [])
    if not isinstance(required, list) or len(required) != 1:
        fail("manifest.json:required_executas", "expected exactly one required Executa")
    else:
        expect_equal("manifest.json:tool_id", required[0].get("tool_id"), BUNDLED_REFERENCE)
        expect_equal("manifest.json:min_version", required[0].get("min_version"), VERSION)
    host_api = manifest.get("ui", {}).get("host_api", {})
    expect_equal("manifest.json:ui.host_api.tools", host_api.get("tools"), ["required:*"])
    expect_equal("manifest.json:ui.host_api.llm", host_api.get("llm"), ["complete"])

    executa = read_json("executas/mini-notes-summary-python/executa.json")
    expect_equal("executa.json:slug", executa.get("slug"), HANDLE)
    expect_equal("executa.json:tool_id", executa.get("tool_id"), LOCAL_TOOL_ID)
    expect_equal("executa.json:version", executa.get("version"), VERSION)


def check_source_contracts() -> None:
    tools = expect_text(
        "src/anna/tools.ts",
        rf'EXECUTA_HANDLE\s*=\s*"{re.escape(HANDLE)}"',
        "Executa handle",
    )
    if f'DEV_TOOL_ID = "{LOCAL_TOOL_ID}"' not in tools:
        fail("src/anna/tools.ts", "frontend fallback tool_id mismatch")
    if f'TOOL_METHOD = "{TOOL_METHOD}"' not in tools:
        fail("src/anna/tools.ts", "frontend Tool method mismatch")
    if "anna.tools.invoke" not in tools:
        fail("src/anna/tools.ts", "frontend anna.tools.invoke call missing")

    for finding in find_direct_llm_calls(ROOT / "src"):
        fail(
            f"{finding.relative_path}:{finding.line_number}",
            f"direct frontend LLM call matched {finding.pattern!r}",
        )

    storage = (ROOT / "src/anna/storage.ts").read_text(encoding="utf-8")
    if f'STORAGE_KEY = "{STORAGE_KEY}"' not in storage:
        fail("src/anna/storage.ts", "storage key mismatch")

    manifest = literal_assignment(
        "executas/mini-notes-summary-python/executa_manifest.py", "MANIFEST"
    )
    if isinstance(manifest, dict):
        expect_equal("executa_manifest.py:name", manifest.get("name"), HANDLE)
        expect_equal("executa_manifest.py:version", manifest.get("version"), VERSION)
        expect_equal(
            "executa_manifest.py:host_capabilities",
            manifest.get("host_capabilities"),
            ["llm.sample"],
        )
        tool_names = [tool.get("name") for tool in manifest.get("tools", [])]
        expect_equal("executa_manifest.py:tools", tool_names, [TOOL_METHOD])

    plugin_method = literal_assignment(
        "executas/mini-notes-summary-python/mini_notes_summary.py", "TOOL_NAME"
    )
    expect_equal("mini_notes_summary.py:TOOL_NAME", plugin_method, TOOL_METHOD)

    pyproject = (ROOT / "executas/mini-notes-summary-python/pyproject.toml").read_text(
        encoding="utf-8"
    )
    if f'name = "{LOCAL_TOOL_ID}"' not in pyproject:
        fail("pyproject.toml", "project/script identity mismatch")
    if f'version = "{VERSION}"' not in pyproject:
        fail("pyproject.toml", "version mismatch")


def check_fixture_and_tests() -> None:
    fixture_path = ROOT / "fixtures/sampling-summary.jsonl"
    entries: List[Dict[str, Any]] = []
    for line_number, raw in enumerate(fixture_path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as error:
            fail(f"fixtures/sampling-summary.jsonl:{line_number}", str(error))
            continue
        entries.append(entry)
    if len(entries) != 1:
        fail("fixtures/sampling-summary.jsonl", "expected exactly one mock entry")
    else:
        expect_equal("fixture:ns", entries[0].get("ns"), "sampling")
        expect_equal("fixture:method", entries[0].get("method"), "createMessage")
        result = entries[0].get("result", {})
        if result.get("content", {}).get("type") != "text":
            fail("fixture:result", "content.type must be text")
        if not result.get("content", {}).get("text"):
            fail("fixture:result", "content.text must be non-empty")

    tests = (ROOT / "executas/mini-notes-summary-python/tests/test_protocol.py").read_text(
        encoding="utf-8"
    )
    if TOOL_METHOD not in tests:
        fail("tests/test_protocol.py", "summarize_notes coverage missing")


def reject_standalone_summarize_method() -> None:
    targets = [
        "app.json",
        "manifest.json",
        "src/anna/tools.ts",
        "executas/mini-notes-summary-python/executa.json",
        "executas/mini-notes-summary-python/executa_manifest.py",
        "executas/mini-notes-summary-python/mini_notes_summary.py",
        "executas/mini-notes-summary-python/tests/test_protocol.py",
    ]
    forbidden = [
        re.compile(r'["\']summarize["\']'),
        re.compile(r'tool\s*==\s*["\']summarize["\']'),
        re.compile(r'method\s*:\s*["\']summarize["\']'),
    ]
    for relative in targets:
        text = (ROOT / relative).read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), 1):
            if any(pattern.search(line) for pattern in forbidden):
                fail(f"{relative}:{line_number}", "standalone summarize Tool method found")


def main() -> int:
    check_json_contracts()
    check_source_contracts()
    check_fixture_and_tests()
    reject_standalone_summarize_method()
    if failures:
        print("identity check failed:", file=sys.stderr)
        for item in failures:
            print(f"- {item}", file=sys.stderr)
        return 1
    print("identity check passed")
    print(f"  app_slug={APP_SLUG}")
    print(f"  handle={HANDLE}")
    print(f"  bundled_reference={BUNDLED_REFERENCE}")
    print(f"  local_tool_id={LOCAL_TOOL_ID}")
    print(f"  tool_method={TOOL_METHOD}")
    print(f"  storage_key={STORAGE_KEY}")
    print(f"  version={VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
