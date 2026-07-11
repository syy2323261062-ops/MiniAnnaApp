#!/usr/bin/env python3
"""Reject direct LLM calls in production frontend source."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
SOURCE_SUFFIXES = {".ts", ".tsx", ".js", ".jsx"}

FORBIDDEN_PATTERNS = (
    re.compile(r"\banna\s*\.\s*llm\s*\.\s*complete\b"),
    re.compile(r"\banna\s*\[\s*[\"']llm[\"']\s*\]"),
    re.compile(r"\.\s*llm\s*\.\s*complete\s*\("),
    re.compile(r"\bllm\s*\.\s*complete\s*\("),
)


@dataclass(frozen=True)
class Finding:
    relative_path: str
    line_number: int
    pattern: str
    line: str


def production_sources(source_root: Path = SOURCE_ROOT) -> Iterable[Path]:
    return sorted(
        path
        for path in source_root.rglob("*")
        if path.is_file() and path.suffix.lower() in SOURCE_SUFFIXES
    )


def find_direct_llm_calls(source_root: Path = SOURCE_ROOT) -> List[Finding]:
    findings: List[Finding] = []
    for path in production_sources(source_root):
        relative = path.relative_to(ROOT).as_posix()
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.search(line):
                    findings.append(
                        Finding(relative, line_number, pattern.pattern, line.strip())
                    )
                    break
    return findings


def main() -> int:
    findings = find_direct_llm_calls()
    if findings:
        print("direct frontend LLM calls found:", file=sys.stderr)
        for finding in findings:
            print(
                f"- {finding.relative_path}:{finding.line_number}: "
                f"{finding.line} (matched {finding.pattern})",
                file=sys.stderr,
            )
        return 1

    print("no direct frontend LLM calls found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
