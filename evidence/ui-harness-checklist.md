# UI Harness Verification

- Date: 2026-07-11 (three real dashboard recordings)
- CLI version: 0.1.37
- Command: `npm run dev:anna:no-llm`
- Browser: user-controlled Chromium dashboard
- Harness URL: `http://localhost:5180/`

## Required by question.md

- App loaded and runtime connected: PASS
- Initial empty state displayed: PASS
- Empty, whitespace-only, and newline-only input blocked: PASS
- Save clears input: PASS
- `anna.storage.get` used: PASS
- `anna.storage.set` used: PASS
- Notes display content and order: PASS
- Delete persisted and removed the note: PASS
- App iframe refresh restored current lifecycle state: PASS
- Summarize re-read current notes: PASS
- `anna.tools.invoke` used with `summarize_notes`: PASS
- Executa emitted `sampling/createMessage`: PASS
- Reverse request reached the CLI `--no-llm` bridge: PASS
- Real `--no-llm` error displayed: PASS — `[-32603] harness started with --no-llm`
- No fallback summary displayed: PASS — Summary area retained only the static empty-state placeholder
- Notes CRUD remained usable after the error: PASS — created and then deleted `错误后仍可保存`

## Additional quality checks

- Versioned storage value contains `version`, `nextOrder`, and `notes`: PASS
- `nextOrder` is monotonic after deletion: PASS
- Deleted order is not reused: PASS
- `window.hello` scopes include `llm.complete`: PASS
- Summarize loading text visually confirmed: NOT RUN — transition was too fast to observe reliably
- Four required UI screenshots captured: PASS
- UI RPC log captured and sanitized: PASS
- Windows binary SHA recorded separately: PASS
- Protocol recording exists: PASS

## Evidence files

- `evidence/ui-empty-state.png`
- `evidence/ui-notes-created.png`
- `evidence/ui-note-deleted.png`
- `evidence/ui-no-llm-error.png`
- `evidence/ui-no-llm-rpc.jsonl`

Only results observed in the real browser/RPC session may be marked PASS. The compatibility declaration in `manifest.json` does not count as UI evidence. Backend Sampling remains independently covered by `npm run executa:mock` and `npm run test:protocol`.

The committed `evidence/ui-no-llm-rpc.jsonl` combines and sanitizes three real dashboard recordings. Raw recordings remain under ignored `harness/` / `evidence/raw/` paths. The log records `window.hello` with `llm.complete`, storage CRUD and monotonic orders, iframe reload followed by `storage.get`, correct `tools.invoke` arguments, the explicit no-LLM bridge error, and successful create/delete operations after the error. Reaching the CLI no-LLM bridge from this Tool invocation is evidence that the Executa reverse Sampling request crossed the compatibility ACL; the independent protocol and mock tests directly record `sampling/createMessage`.
