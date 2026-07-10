#!/usr/bin/env python3
"""Smoke-test a packaged Mini Notes Summary executable over JSON-RPC stdio."""

from __future__ import annotations

import argparse
import json
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, TextIO


TIMEOUT_SECONDS = 90.0


def pump_lines(
    stream: TextIO,
    output: "queue.Queue[str | None]",
    captured: list[str],
) -> None:
    try:
        for line in stream:
            value = line.rstrip("\r\n")
            captured.append(value)
            output.put(value)
    finally:
        output.put(None)


def send_request(process: subprocess.Popen[str], request: dict[str, Any]) -> None:
    if process.stdin is None:
        raise RuntimeError("binary stdin is unavailable")
    process.stdin.write(json.dumps(request, ensure_ascii=False, separators=(",", ":")))
    process.stdin.write("\n")
    process.stdin.flush()


def read_response(
    stdout_queue: "queue.Queue[str | None]",
    expected_id: int,
    deadline: float,
) -> dict[str, Any]:
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError(f"timed out waiting for JSON-RPC response id={expected_id}")
        try:
            line = stdout_queue.get(timeout=remaining)
        except queue.Empty as error:
            raise RuntimeError(
                f"timed out waiting for JSON-RPC response id={expected_id}"
            ) from error
        if line is None:
            raise RuntimeError(
                f"binary stdout closed before JSON-RPC response id={expected_id}"
            )
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as error:
            raise RuntimeError(f"non-JSON data appeared on binary stdout: {line!r}") from error
        if not isinstance(message, dict):
            raise RuntimeError(f"binary stdout JSON must be an object: {line!r}")
        if message.get("id") != expected_id:
            raise RuntimeError(
                f"unexpected JSON-RPC response id {message.get('id')!r}; "
                f"expected {expected_id}"
            )
        if "error" in message:
            raise RuntimeError(
                f"JSON-RPC request id={expected_id} failed: {message['error']!r}"
            )
        return message


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run_smoke(binary: Path) -> None:
    binary = binary.resolve()
    if not binary.is_file():
        raise RuntimeError(f"binary does not exist: {binary}")

    process = subprocess.Popen(
        [str(binary)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="strict",
        bufsize=1,
    )
    if process.stdout is None or process.stderr is None:
        process.kill()
        raise RuntimeError("failed to capture binary stdout/stderr")

    stdout_queue: "queue.Queue[str | None]" = queue.Queue()
    stderr_queue: "queue.Queue[str | None]" = queue.Queue()
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    stdout_thread = threading.Thread(
        target=pump_lines,
        args=(process.stdout, stdout_queue, stdout_lines),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=pump_lines,
        args=(process.stderr, stderr_queue, stderr_lines),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()

    try:
        deadline = time.monotonic() + TIMEOUT_SECONDS
        send_request(
            process,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2.0"},
            },
        )
        initialized = read_response(stdout_queue, 1, deadline)["result"]
        require(
            initialized.get("protocolVersion") == "2.0",
            "initialize protocolVersion must equal 2.0",
        )
        require(
            initialized.get("client_capabilities", {}).get("sampling") == {},
            "initialize client_capabilities.sampling must equal {}",
        )

        send_request(
            process,
            {"jsonrpc": "2.0", "id": 2, "method": "describe", "params": {}},
        )
        manifest = read_response(stdout_queue, 2, deadline)["result"]
        require(manifest.get("name") == "mini-notes-summary", "describe name mismatch")
        require(manifest.get("version") == "0.1.0", "describe version mismatch")
        require(
            "llm.sample" in manifest.get("host_capabilities", []),
            "describe host_capabilities must contain llm.sample",
        )
        tool_names = [tool.get("name") for tool in manifest.get("tools", [])]
        require(
            "summarize_notes" in tool_names,
            "describe tools must contain summarize_notes",
        )

        send_request(
            process,
            {"jsonrpc": "2.0", "id": 3, "method": "health", "params": {}},
        )
        health = read_response(stdout_queue, 3, deadline)["result"]
        require(health.get("status") == "healthy", "health status must be healthy")

        send_request(
            process,
            {"jsonrpc": "2.0", "id": 4, "method": "shutdown", "params": {}},
        )
        shutdown = read_response(stdout_queue, 4, deadline)["result"]
        require(shutdown.get("ok") is True, "shutdown result.ok must be true")
        if process.stdin is not None:
            process.stdin.close()
        process.wait(timeout=max(1.0, deadline - time.monotonic()))
        require(process.returncode == 0, f"binary exited with code {process.returncode}")
    except Exception:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=10)
        raise
    finally:
        stdout_thread.join(timeout=5)
        stderr_thread.join(timeout=5)

    for line in stdout_lines:
        if line.strip():
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                raise RuntimeError(f"non-JSON data appeared on stdout: {line!r}") from error
            require(isinstance(value, dict), "every stdout JSON value must be an object")

    print(
        "Binary smoke passed: initialize, describe, health, shutdown; "
        f"stdout_json_lines={len([line for line in stdout_lines if line.strip()])}; "
        f"stderr_lines={len([line for line in stderr_lines if line.strip()])}; "
        f"size={binary.stat().st_size} bytes"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    args = parser.parse_args()
    run_smoke(args.binary)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"smoke_binary.py: {error}", file=sys.stderr)
        raise SystemExit(1) from error
