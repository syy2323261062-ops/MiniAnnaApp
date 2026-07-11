from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "sanitize_ui_rpc_log.py"


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )


def test_removes_auth_refresh_redacts_tokens_and_keeps_rpc(tmp_path: Path) -> None:
    raw = tmp_path / "raw.jsonl"
    output = tmp_path / "sanitized.jsonl"
    write_jsonl(
        raw,
        [
            {"kind": "event", "event": "auth.refresh", "token": "drop-me"},
            {
                "kind": "req",
                "ns": "storage",
                "method": "get",
                "args": {"key": "mini-notes:notes:v1"},
            },
            {
                "kind": "req",
                "ns": "tools",
                "method": "invoke",
                "authorization": "Bearer secret-value",
                "args": {
                    "method": "summarize_notes",
                    "token": "nested-secret",
                },
            },
        ],
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(raw), str(output)],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 2
    assert records[0]["ns"] == "storage"
    assert records[1]["ns"] == "tools"
    assert records[1]["authorization"] == "[REDACTED]"
    assert records[1]["args"]["token"] == "[REDACTED]"
    serialized = output.read_text(encoding="utf-8")
    assert "auth.refresh" not in serialized
    assert "drop-me" not in serialized
    assert "secret-value" not in serialized
    assert "nested-secret" not in serialized
