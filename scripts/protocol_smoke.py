#!/usr/bin/env python3
"""Drive and optionally record a complete offline Executa sampling exchange."""

from __future__ import annotations

import argparse
import json
import queue
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
EXECUTA = (
    REPO_ROOT
    / "executas"
    / "mini-notes-summary-python"
    / "mini_notes_summary.py"
)
MOCK_SUMMARY = "这些笔记主要涉及客户跟进、登录问题修复和 Workshop 内容准备。"
NOTES = [
    {"id": "n1", "order": 1, "content": "明天跟客户 follow up"},
    {"id": "n2", "order": 2, "content": "修复登录 bug"},
    {"id": "n3", "order": 3, "content": "准备 Workshop 内容"},
]


class ProtocolFailure(RuntimeError):
    pass


class JsonLineReader:
    def __init__(self, stream: Any) -> None:
        self._stream = stream
        self._frames: "queue.Queue[Tuple[str, Optional[Dict[str, Any]], Optional[Exception]]]" = queue.Queue()
        self.lines: List[str] = []
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        for raw in self._stream:
            line = raw.rstrip("\r\n")
            if not line:
                continue
            self.lines.append(line)
            try:
                parsed = json.loads(line)
                if not isinstance(parsed, dict):
                    raise ValueError("JSON-RPC frame must be an object")
                self._frames.put((line, parsed, None))
            except Exception as error:  # noqa: BLE001
                self._frames.put((line, None, error))

    def read(self, timeout: float = 8.0) -> Dict[str, Any]:
        try:
            raw, frame, error = self._frames.get(timeout=timeout)
        except queue.Empty as exc:
            raise ProtocolFailure("timed out waiting for Executa stdout") from exc
        if error is not None:
            raise ProtocolFailure(f"non-JSON stdout line: {raw!r}: {error}")
        assert frame is not None
        return frame

    def join(self) -> None:
        self._thread.join(timeout=2)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ProtocolFailure(message)


def send_frame(process: subprocess.Popen[str], frame: Dict[str, Any]) -> None:
    if process.stdin is None:
        raise ProtocolFailure("Executa stdin is unavailable")
    process.stdin.write(json.dumps(frame, ensure_ascii=False) + "\n")
    process.stdin.flush()


def record(records: List[Dict[str, Any]], event: str, frame: Dict[str, Any]) -> None:
    records.append({"event": event, "frame": frame})


def run(record_path: Optional[Path]) -> None:
    require(sys.version_info >= (3, 10), "protocol smoke requires Python 3.10+")
    require(EXECUTA.is_file(), f"Executa not found: {EXECUTA}")

    process = subprocess.Popen(
        [sys.executable, str(EXECUTA)],
        cwd=str(EXECUTA.parent),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        bufsize=1,
    )
    assert process.stdout is not None
    assert process.stderr is not None
    stdout = JsonLineReader(process.stdout)
    stderr_lines: List[str] = []
    stderr_thread = threading.Thread(
        target=lambda: stderr_lines.extend(line.rstrip("\r\n") for line in process.stderr),
        daemon=True,
    )
    stderr_thread.start()
    records: List[Dict[str, Any]] = []

    try:
        initialize_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2.0"},
        }
        record(records, "host.initialize.request", initialize_request)
        send_frame(process, initialize_request)
        initialize_response = stdout.read()
        record(records, "tool.initialize.response", initialize_response)
        require(
            initialize_response.get("result", {}).get("protocolVersion") == "2.0",
            "initialize did not negotiate protocol 2.0",
        )
        require(
            initialize_response.get("result", {}).get("client_capabilities", {}).get("sampling") == {},
            "initialize did not advertise client_capabilities.sampling",
        )

        describe_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "describe",
        }
        record(records, "host.describe.request", describe_request)
        send_frame(process, describe_request)
        describe_response = stdout.read()
        record(records, "tool.describe.response", describe_response)
        manifest = describe_response.get("result", {})
        require(manifest.get("name") == "mini-notes-summary", "manifest name mismatch")
        require(manifest.get("version") == "0.1.0", "manifest version mismatch")
        require("llm.sample" in manifest.get("host_capabilities", []), "llm.sample missing")
        require(
            [tool.get("name") for tool in manifest.get("tools", [])] == ["summarize_notes"],
            "summarize_notes tool mismatch",
        )

        invoke_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "invoke",
            "params": {
                "tool": "summarize_notes",
                "arguments": {"notes": NOTES},
                "invoke_id": "protocol-smoke-invoke-1",
            },
        }
        record(records, "host.invoke.request", invoke_request)
        send_frame(process, invoke_request)

        sampling_request = stdout.read()
        record(records, "tool.sampling.request", sampling_request)
        require(
            sampling_request.get("method") == "sampling/createMessage",
            "Tool did not emit sampling/createMessage",
        )
        sampling_params = sampling_request.get("params", {})
        prompt = sampling_params.get("messages", [{}])[0].get("content", {}).get("text", "")
        for note in NOTES:
            require(note["content"] in prompt, f"sampling prompt missing note: {note['content']}")
        metadata = sampling_params.get("metadata", {})
        require(bool(metadata.get("executa_invoke_id")), "metadata.executa_invoke_id missing")
        require(metadata.get("tool") == "summarize_notes", "metadata.tool mismatch")
        require(metadata.get("note_count") == 3, "metadata.note_count mismatch")

        sampling_response = {
            "jsonrpc": "2.0",
            "id": sampling_request.get("id"),
            "result": {
                "role": "assistant",
                "content": {"type": "text", "text": MOCK_SUMMARY},
                "model": "mock-mini-notes",
                "stopReason": "endTurn",
                "usage": {"inputTokens": 72, "outputTokens": 18, "totalTokens": 90},
            },
        }
        record(records, "host.sampling.response", sampling_response)
        send_frame(process, sampling_response)

        invoke_response = stdout.read()
        record(records, "tool.invoke.response", invoke_response)
        result = invoke_response.get("result", {})
        require(result.get("success") is True, "invoke success was not true")
        require(result.get("tool") == "summarize_notes", "invoke tool mismatch")
        require(result.get("data", {}).get("summary") == MOCK_SUMMARY, "summary mismatch")

        shutdown_request = {"jsonrpc": "2.0", "id": 4, "method": "shutdown"}
        record(records, "host.shutdown.request", shutdown_request)
        send_frame(process, shutdown_request)
        shutdown_response = stdout.read()
        record(records, "tool.shutdown.response", shutdown_response)
        require(shutdown_response.get("result", {}).get("ok") is True, "shutdown failed")

        assert process.stdin is not None
        process.stdin.close()
        process.wait(timeout=8)
        require(process.returncode == 0, f"Executa exited with code {process.returncode}")
        stdout.join()
        stderr_thread.join(timeout=2)
        for line in stdout.lines:
            parsed = json.loads(line)
            require(isinstance(parsed, dict), "stdout contained non-object JSON")

        if record_path is not None:
            destination = record_path if record_path.is_absolute() else REPO_ROOT / record_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records),
                encoding="utf-8",
            )
            print(f"recorded {len(records)} protocol events to {destination}")
        print(f"protocol smoke passed: {len(stdout.lines)} stdout JSON frames")
    finally:
        if process.poll() is None:
            if process.stdin is not None and not process.stdin.closed:
                process.stdin.close()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=3)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", type=Path, help="write protocol evidence JSONL")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    try:
        run(arguments.record)
    except (ProtocolFailure, subprocess.TimeoutExpired) as error:
        print(f"protocol smoke failed: {error}", file=sys.stderr)
        raise SystemExit(1)

