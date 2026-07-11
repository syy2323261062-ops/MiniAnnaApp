# question.md acceptance matrix

Status values are intentionally limited to `PASS`, `FAIL`, `BLOCKED`, and `NOT RUN`. UI and native-build rows must be updated only from evidence produced by the current final-acceptance run.

| Requirement | Implementation | Command / Evidence | Status |
|---|---|---|---|
| App manifest | `manifest.json` schema 2, permissions, required Executa, UI bundle/views/Host API, dev config | `npm run validate` | PASS |
| app.json | App identity and bundled `mini-notes-summary` path | `app.json`; `npm run check:identity` | PASS |
| React / TypeScript / Vite | `src/main.tsx`, `src/App.tsx`, `vite.config.ts`, `base: "./"`, root `bundle/` output | `npm run build` | PASS |
| AnnaAppRuntime.connect | Dynamic production SDK import and singleton connection | `src/anna/runtime.ts` | PASS |
| Storage get/set | Versioned value under `mini-notes:notes:v1` via Anna Host API only | `src/anna/storage.ts`; final UI RPC log | NOT RUN |
| Empty input | `draft.trim()` guards button and submit handler | Final UI empty/whitespace/newline interaction | NOT RUN |
| Save clears input | `setDraft("")` after successful Host API write | Final UI interaction | NOT RUN |
| Ordered list | Persisted `nextOrder`; UI renders note order | Final UI notes screenshot and RPC log | NOT RUN |
| Delete | Storage read, filtered value write, immediate render update | Final UI delete screenshot and RPC log | NOT RUN |
| tools.invoke | Frontend resolves bundled handle/dev tool ID and invokes `summarize_notes` with note objects | `src/anna/tools.ts`; final UI RPC log | NOT RUN |
| Executa JSON-RPC over stdio | Long-lived newline reader, locked/flushed stdout, stderr logging | Executa pytest; `npm run test:protocol` | PASS |
| initialize protocol v2 | Negotiates `protocolVersion: "2.0"` | `test_initialize_negotiates_v2_sampling`; protocol evidence | PASS |
| client_capabilities.sampling | Returns `client_capabilities.sampling = {}` for v2 | Executa pytest; `evidence/protocol-smoke.jsonl` | PASS |
| describe bare manifest | Returns `MANIFEST` without wrapper | `test_describe_returns_bare_manifest` | PASS |
| Tool parameters[] | `summarize_notes` uses Anna `parameters[]` with object-array note schema | `executa_manifest.py`; Executa pytest | PASS |
| sampling/createMessage | Vendored `SamplingClient.create_message` reverse RPC | `npm run test:protocol`; `npm run executa:mock` | PASS |
| Sampling invoke metadata | `executa_invoke_id`, tool, and note count | Protocol smoke assertions/evidence | PASS |
| Shared stdin reader | Reverse responses dispatched before invoke worker queue; independent asyncio loop and thread pool | `mini_notes_summary.py`; reverse round-trip pytest | PASS |
| Mock Sampling fixture | Offline `sampling/createMessage` result in JSONL fixture | `fixtures/sampling-summary.jsonl`; `npm run executa:mock` | PASS |
| Protocol smoke | initialize, describe, health, invoke, reverse response, shutdown, JSON-only stdout | `npm run test:protocol`; `evidence/protocol-smoke.jsonl` | PASS |
| `--no-llm` UI harness | Clean legacy-state UI session must reach the explicit no-LLM bridge error | Final screenshots and sanitized UI RPC JSONL | NOT RUN |
| Windows onefile binary | PyInstaller onefile native executable | `npm run build:binary`; `evidence/binary-windows.md` | PASS |
| Archive root manifest | Binary archive root contains runtime `manifest.json` and `bin/mini-notes-summary.exe` only | `scripts/verify_archive.py`; binary evidence | PASS |
| darwin-arm64 workflow | Native `macos-15` matrix entry and `.tar.gz` asset | `npm run check:workflow` | PASS |
| darwin-x86_64 workflow | Native `macos-15-intel` matrix entry and `.tar.gz` asset | `npm run check:workflow` | PASS |
| windows-x86_64 workflow | Native `windows-latest` matrix entry and `.zip` asset | `npm run check:workflow` | PASS |
| GitHub Release assets | Release job requires and uploads the exact three archive names | Static workflow check passes; real workflow/Release prohibited in this stage | NOT RUN |
| README | Structure, setup, build, strict validation, no-LLM UI, mock Sampling, protocol, storage, binary and Release documentation | `README.md` review | PASS |
| GitHub repository | Remote `syy2323261062-ops/MiniAnnaApp`; final changes must be committed/pushed only after authorization | Final Git status; commit/push prohibited in this stage | BLOCKED |
