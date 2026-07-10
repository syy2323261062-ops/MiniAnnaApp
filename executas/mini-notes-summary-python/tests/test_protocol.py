from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Dict

import pytest


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_DIR / "mini_notes_summary.py"
sys.path.insert(0, str(PROJECT_DIR))

import mini_notes_summary as plugin  # noqa: E402


def _request(method: str, *, request_id: int = 1, params: Any = None) -> Dict[str, Any]:
    message: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
    }
    if params is not None:
        message["params"] = params
    return message


def _invoke(notes: Any, *, tool: str = "summarize_notes") -> Dict[str, Any]:
    return plugin._dispatch_request(
        _request(
            "invoke",
            params={
                "tool": tool,
                "arguments": {"notes": notes},
                "invoke_id": "unit-invoke",
            },
        )
    )


def _send_json(process: subprocess.Popen[str], message: Dict[str, Any]) -> None:
    assert process.stdin is not None
    process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
    process.stdin.flush()


def _read_json(process: subprocess.Popen[str], timeout: float = 8.0) -> Dict[str, Any]:
    assert process.stdout is not None
    output: "queue.Queue[str]" = queue.Queue(maxsize=1)

    def read_line() -> None:
        output.put(process.stdout.readline())

    threading.Thread(target=read_line, daemon=True).start()
    try:
        raw_line = output.get(timeout=timeout)
    except queue.Empty as error:
        raise AssertionError("timed out waiting for Executa stdout") from error
    assert raw_line, "Executa exited before returning a JSON-RPC frame"
    return json.loads(raw_line)


def _stop_process(process: subprocess.Popen[str]) -> tuple[str, str]:
    if process.stdin is not None and not process.stdin.closed:
        process.stdin.close()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)
    stdout = process.stdout.read() if process.stdout is not None else ""
    stderr = process.stderr.read() if process.stderr is not None else ""
    return stdout, stderr


def test_initialize_negotiates_v2_sampling() -> None:
    response = plugin._dispatch_request(
        _request("initialize", params={"protocolVersion": "2.0"})
    )
    assert response["result"]["protocolVersion"] == "2.0"
    assert response["result"]["client_capabilities"] == {"sampling": {}}


def test_describe_returns_bare_manifest() -> None:
    response = plugin._dispatch_request(_request("describe"))
    assert response["result"] is plugin.MANIFEST
    assert "manifest" not in response["result"]


def test_manifest_has_required_identity_and_capability() -> None:
    assert plugin.MANIFEST["name"] == "mini-notes-summary"
    assert plugin.MANIFEST["version"] == "0.1.0"
    assert plugin.MANIFEST["host_capabilities"] == ["llm.sample"]


def test_manifest_tool_uses_parameters_and_object_note_items() -> None:
    tool = plugin.MANIFEST["tools"][0]
    assert tool["name"] == "summarize_notes"
    assert "parameters" in tool
    assert "input_schema" not in tool
    notes_parameter = tool["parameters"][0]
    assert notes_parameter["name"] == "notes"
    assert notes_parameter["type"] == "array"
    assert notes_parameter["items_type"] == "object"
    assert notes_parameter["items"]["required"] == ["id", "order", "content"]


def test_health_is_healthy() -> None:
    response = plugin._dispatch_request(_request("health"))
    assert response["result"]["status"] == "healthy"
    assert response["result"]["version"] == "0.1.0"


def test_unknown_method_returns_method_not_found() -> None:
    response = plugin._dispatch_request(_request("missing_method"))
    assert response["error"]["code"] == -32601


def test_unknown_tool_returns_method_not_found() -> None:
    response = _invoke([], tool="missing_tool")
    assert response["error"]["code"] == -32601


@pytest.mark.parametrize("notes", ["not-an-array", {"content": "note"}, 42])
def test_notes_type_error_returns_invalid_params(notes: Any) -> None:
    response = _invoke(notes)
    assert response["error"]["code"] == -32602
    assert "notes" in response["error"]["message"]


@pytest.mark.parametrize(
    "notes",
    [
        [],
        [{"id": "n1", "order": 1, "content": "   "}],
    ],
)
def test_empty_notes_return_invalid_params_without_sampling(notes: Any) -> None:
    response = _invoke(notes)
    assert response["error"]["code"] == -32602


def test_parse_error_is_json_rpc_error(capsys: pytest.CaptureFixture[str]) -> None:
    plugin._route_line("{invalid-json")
    stdout = capsys.readouterr().out.strip()
    response = json.loads(stdout)
    assert response["error"]["code"] == -32700


def test_stdout_contains_only_json_rpc_frames() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        input=json.dumps(_request("describe")) + "\n",
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert completed.returncode == 0
    stdout_lines = [line for line in completed.stdout.splitlines() if line.strip()]
    assert len(stdout_lines) == 1
    assert json.loads(stdout_lines[0])["result"]["name"] == "mini-notes-summary"
    assert "Executa started" not in completed.stdout
    assert "Executa started" in completed.stderr


def test_reverse_sampling_round_trip_subprocess() -> None:
    process = subprocess.Popen(
        [sys.executable, str(SCRIPT_PATH)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        bufsize=1,
    )
    remaining_stdout = ""
    stderr = ""
    try:
        _send_json(
            process,
            _request(
                "initialize",
                request_id=1,
                params={"protocolVersion": "2.0"},
            ),
        )
        initialized = _read_json(process)
        assert initialized["id"] == 1
        assert initialized["result"]["client_capabilities"] == {"sampling": {}}

        _send_json(
            process,
            _request(
                "invoke",
                request_id=2,
                params={
                    "tool": "summarize_notes",
                    "arguments": {
                        "notes": [
                            {"id": "later", "order": 2, "content": "Prepare beta demo"},
                            {"id": "first", "order": 1, "content": "Call alpha client"},
                        ]
                    },
                    "invoke_id": "integration-invoke-42",
                },
            ),
        )

        sampling_request = _read_json(process)
        assert sampling_request["method"] == "sampling/createMessage"
        prompt = sampling_request["params"]["messages"][0]["content"]["text"]
        assert "Call alpha client" in prompt
        assert "Prepare beta demo" in prompt
        assert prompt.index("Call alpha client") < prompt.index("Prepare beta demo")
        assert sampling_request["params"]["metadata"] == {
            "executa_invoke_id": "integration-invoke-42",
            "tool": "summarize_notes",
            "note_count": 2,
        }

        _send_json(
            process,
            {
                "jsonrpc": "2.0",
                "id": sampling_request["id"],
                "result": {
                    "role": "assistant",
                    "content": {"type": "text", "text": "Mock summary from sampling."},
                    "model": "mock-model",
                    "usage": {"inputTokens": 20, "outputTokens": 5, "totalTokens": 25},
                    "stopReason": "endTurn",
                },
            },
        )

        invoke_response = _read_json(process)
        assert invoke_response["id"] == 2
        assert invoke_response["result"] == {
            "success": True,
            "tool": "summarize_notes",
            "data": {
                "summary": "Mock summary from sampling.",
                "model": "mock-model",
                "usage": {"inputTokens": 20, "outputTokens": 5, "totalTokens": 25},
                "stopReason": "endTurn",
            },
        }
    finally:
        remaining_stdout, stderr = _stop_process(process)

    assert not remaining_stdout.strip()
    assert "Executa started" in stderr

