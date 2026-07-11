#!/usr/bin/env python3
"""Sanitize a dashboard JSONL recording before it enters evidence/."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


REDACTED = "[REDACTED]"
SENSITIVE_KEYS = {
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "cookie",
    "bearer",
    "pat",
    "credentials",
}
JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
BEARER_RE = re.compile(r"(?i)\bBearer\s+[^\s\"']+")


def is_sensitive_key(key: str) -> bool:
    normalized = key.casefold()
    return normalized in SENSITIVE_KEYS or normalized.endswith("_token")


def is_auth_refresh(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    for key, item in value.items():
        if key.casefold() in {"event", "method", "name"} and item == "auth.refresh":
            return True
        if isinstance(item, (dict, list)) and is_auth_refresh(item):
            return True
    return False


def sanitize_string(value: str) -> str:
    value = JWT_RE.sub(REDACTED, value)
    return BEARER_RE.sub(f"Bearer {REDACTED}", value)


def sanitize_value(value: Any, sensitive_values: set[str]) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if is_sensitive_key(str(key)):
                if isinstance(item, str) and item:
                    sensitive_values.add(item)
                sanitized[key] = REDACTED
            else:
                sanitized[key] = sanitize_value(item, sensitive_values)
        return sanitized
    if isinstance(value, list):
        return [sanitize_value(item, sensitive_values) for item in value]
    if isinstance(value, str):
        return sanitize_string(value)
    return value


def sanitized_lines(input_path: Path) -> tuple[list[str], set[str]]:
    output: list[str] = []
    sensitive_values: set[str] = set()
    with input_path.open("r", encoding="utf-8") as source:
        for line_number, raw in enumerate(source, 1):
            line = raw.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                print(
                    f"warning: {input_path}:{line_number}: invalid JSONL skipped: {error}",
                    file=sys.stderr,
                )
                continue
            if is_auth_refresh(record):
                continue
            sanitized = sanitize_value(record, sensitive_values)
            output.append(json.dumps(sanitized, ensure_ascii=False, separators=(",", ":")))
    return output, sensitive_values


def validate_output(text: str, sensitive_values: Iterable[str]) -> None:
    if JWT_RE.search(text):
        raise RuntimeError("sanitized output still contains a JWT-like value")
    for value in sensitive_values:
        if value and value != REDACTED and value in text:
            raise RuntimeError("sanitized output still contains an original secret value")


def sanitize_file(input_path: Path, output_path: Path, *, force: bool = False) -> int:
    input_resolved = input_path.resolve()
    output_resolved = output_path.resolve()
    if input_resolved == output_resolved:
        raise RuntimeError("refusing to overwrite the input recording")
    if not input_resolved.is_file():
        raise RuntimeError(f"input recording does not exist: {input_resolved}")
    if output_resolved.exists() and not force:
        raise RuntimeError(f"output already exists (use --force): {output_resolved}")

    lines, sensitive_values = sanitized_lines(input_resolved)
    text = "".join(line + "\n" for line in lines)
    validate_output(text, sensitive_values)
    output_resolved.parent.mkdir(parents=True, exist_ok=True)
    output_resolved.write_text(text, encoding="utf-8", newline="\n")
    print(f"sanitized {len(lines)} JSONL records to {output_resolved}")
    return len(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="raw dashboard recording outside evidence/")
    parser.add_argument("output", type=Path, help="sanitized UTF-8 JSONL destination")
    parser.add_argument("--force", action="store_true", help="replace an existing output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sanitize_file(args.input, args.output, force=args.force)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError) as error:
        print(f"sanitize_ui_rpc_log.py: {error}", file=sys.stderr)
        raise SystemExit(1) from error
