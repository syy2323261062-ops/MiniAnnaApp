#!/usr/bin/env python3
"""Mini Notes Summary Executa using host reverse sampling over JSON-RPC stdio."""

from __future__ import annotations

import asyncio
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List

from executa_sdk import (  # noqa: E402
    PROTOCOL_VERSION_V2,
    SamplingClient,
    SamplingError,
)

from executa_manifest import MANIFEST  # noqa: E402


TOOL_NAME = "summarize_notes"
_stdout_lock = threading.Lock()


class InvalidParamsError(ValueError):
    """Raised when an invoke payload does not match the tool contract."""


def _write_frame(message: Dict[str, Any]) -> None:
    payload = json.dumps(message, ensure_ascii=False, separators=(",", ":"))
    with _stdout_lock:
        sys.stdout.write(payload + "\n")
        sys.stdout.flush()


sampling = SamplingClient(write_frame=_write_frame)


def _make_response(
    request_id: Any,
    *,
    result: Any = None,
    error: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    response: Dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    if error is None:
        response["result"] = result
    else:
        response["error"] = error
    return response


def _clean_notes(notes: Any) -> List[Dict[str, Any]]:
    if not isinstance(notes, list):
        raise InvalidParamsError("'notes' must be an array of note objects")

    cleaned: List[Dict[str, Any]] = []
    for index, note in enumerate(notes):
        if not isinstance(note, dict):
            raise InvalidParamsError(f"notes[{index}] must be an object")

        note_id = note.get("id")
        order = note.get("order")
        content = note.get("content")
        if not isinstance(note_id, str) or not note_id:
            raise InvalidParamsError(f"notes[{index}].id must be a non-empty string")
        if isinstance(order, bool) or not isinstance(order, int) or order < 1:
            raise InvalidParamsError(f"notes[{index}].order must be a positive integer")
        if not isinstance(content, str):
            raise InvalidParamsError(f"notes[{index}].content must be a string")

        normalized_content = content.strip()
        if not normalized_content:
            continue
        cleaned.append(
            {"id": note_id, "order": order, "content": normalized_content}
        )

    if not cleaned:
        raise InvalidParamsError("'notes' must contain at least one non-empty note")
    cleaned.sort(key=lambda item: item["order"])
    return cleaned


def _build_prompt(notes: List[Dict[str, Any]]) -> str:
    ordered_lines = "\n".join(
        f"{position}. [添加顺序 {note['order']}] {note['content']}"
        for position, note in enumerate(notes, start=1)
    )
    return (
        "请整理下面按添加顺序排列的笔记。\n"
        "要求：\n"
        "1. 给出简洁、准确的整体总结。\n"
        "2. 提取主要主题和明确的待办事项。\n"
        "3. 不添加原笔记中不存在的信息。\n"
        "4. 直接返回总结内容，不要添加无关前言。\n\n"
        f"笔记：\n{ordered_lines}"
    )


async def _summarize_notes(notes: Any, *, invoke_id: str) -> Dict[str, Any]:
    cleaned_notes = _clean_notes(notes)
    result = await sampling.create_message(
        messages=[
            {
                "role": "user",
                "content": {"type": "text", "text": _build_prompt(cleaned_notes)},
            }
        ],
        max_tokens=400,
        system_prompt="你是一名简洁、准确的笔记整理助手。",
        metadata={
            "executa_invoke_id": invoke_id,
            "tool": TOOL_NAME,
            "note_count": len(cleaned_notes),
        },
        timeout=60.0,
    )

    content = result.get("content") or {}
    if not isinstance(content, dict) or content.get("type") != "text":
        raise RuntimeError("sampling response did not contain text content")
    summary = content.get("text")
    if not isinstance(summary, str) or not summary.strip():
        raise RuntimeError("sampling response contained an empty summary")

    return {
        "summary": summary.strip(),
        "model": result.get("model"),
        "usage": result.get("usage"),
        "stopReason": result.get("stopReason"),
    }


def _handle_initialize(request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    protocol = params.get("protocolVersion") or "1.1"
    negotiated_v2 = protocol == PROTOCOL_VERSION_V2
    if not negotiated_v2:
        sampling.disable(
            "host did not negotiate Executa protocol 2.0 "
            f"(offered protocolVersion={protocol!r}); sampling is unavailable"
        )
    return _make_response(
        request_id,
        result={
            "protocolVersion": protocol,
            "serverInfo": {
                "name": MANIFEST["display_name"],
                "version": MANIFEST["version"],
            },
            "client_capabilities": {"sampling": {}} if negotiated_v2 else {},
            "capabilities": {},
        },
    )


def _handle_describe(request_id: Any) -> Dict[str, Any]:
    return _make_response(request_id, result=MANIFEST)


def _handle_health(request_id: Any) -> Dict[str, Any]:
    return _make_response(
        request_id,
        result={
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": MANIFEST["version"],
        },
    )


_event_loop = asyncio.new_event_loop()
_event_loop_thread = threading.Thread(
    target=_event_loop.run_forever,
    name="mini-notes-summary-asyncio",
    daemon=True,
)
_event_loop_thread.start()


def _handle_invoke(request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    tool = params.get("tool")
    if tool != TOOL_NAME:
        return _make_response(
            request_id,
            error={"code": -32601, "message": f"Unknown tool: {tool}"},
        )

    arguments = params.get("arguments") or {}
    if not isinstance(arguments, dict):
        return _make_response(
            request_id,
            error={"code": -32602, "message": "Invalid params: arguments must be an object"},
        )
    invoke_id = params.get("invoke_id") or ""
    future = asyncio.run_coroutine_threadsafe(
        _summarize_notes(arguments.get("notes"), invoke_id=str(invoke_id)),
        _event_loop,
    )
    try:
        data = future.result(timeout=90.0)
    except InvalidParamsError as error:
        return _make_response(
            request_id,
            error={"code": -32602, "message": f"Invalid params: {error}"},
        )
    except SamplingError as error:
        return _make_response(
            request_id,
            error={"code": error.code, "message": error.message, "data": error.data},
        )
    except TimeoutError:
        future.cancel()
        return _make_response(
            request_id,
            error={"code": -32603, "message": "Tool execution timed out"},
        )
    except Exception as error:  # noqa: BLE001
        return _make_response(
            request_id,
            error={"code": -32603, "message": f"Tool execution failed: {error}"},
        )
    return _make_response(
        request_id,
        result={"success": True, "tool": TOOL_NAME, "data": data},
    )


def _dispatch_request(message: Dict[str, Any]) -> Dict[str, Any]:
    request_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}
    if not isinstance(params, dict):
        return _make_response(
            request_id,
            error={"code": -32602, "message": "Invalid params: params must be an object"},
        )

    if method == "initialize":
        return _handle_initialize(request_id, params)
    if method == "describe":
        return _handle_describe(request_id)
    if method == "invoke":
        return _handle_invoke(request_id, params)
    if method == "health":
        return _handle_health(request_id)
    if method == "shutdown":
        return _make_response(request_id, result={"ok": True})
    return _make_response(
        request_id,
        error={"code": -32601, "message": f"Method not found: {method}"},
    )


def _write_request_response(message: Dict[str, Any]) -> None:
    response = _dispatch_request(message)
    if message.get("id") is not None:
        _write_frame(response)


def _route_line(line: str, pool: ThreadPoolExecutor | None = None) -> None:
    try:
        message = json.loads(line)
    except json.JSONDecodeError:
        _write_frame(
            _make_response(None, error={"code": -32700, "message": "Parse error"})
        )
        return

    if not isinstance(message, dict):
        _write_frame(
            _make_response(
                None,
                error={"code": -32600, "message": "Invalid Request"},
            )
        )
        return

    # Reverse-RPC responses are dispatched by the stdin reader itself. They
    # never wait behind invoke workers, so even a full worker pool cannot
    # deadlock pending sampling calls.
    if "method" not in message:
        if not sampling.dispatch_response(message):
            print(
                f"unmatched reverse-RPC response id={message.get('id')!r}",
                file=sys.stderr,
            )
        return

    if pool is not None and message.get("method") == "invoke":
        pool.submit(_write_request_response, message)
    else:
        _write_request_response(message)


def _configure_stdio_utf8() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, 'reconfigure', None)
        if callable(reconfigure):
            reconfigure(encoding='utf-8', errors='strict')


def main() -> None:
    _configure_stdio_utf8()
    print("mini-notes-summary Executa started", file=sys.stderr)
    pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="invoke")
    try:
        for raw_line in sys.stdin:
            line = raw_line.strip()
            if line:
                _route_line(line, pool)
    finally:
        pool.shutdown(wait=True, cancel_futures=False)
        _event_loop.call_soon_threadsafe(_event_loop.stop)


if __name__ == "__main__":
    main()
