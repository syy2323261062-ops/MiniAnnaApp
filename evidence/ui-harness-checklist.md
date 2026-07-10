# UI Harness Verification

- Date: 2026-07-11 (RPC log review)
- CLI version: 0.1.37
- Command: `npm run dev:anna:no-llm`
- Browser:
- Harness URL: `http://localhost:5180/`
- App loaded: PENDING
- Runtime connected: PASS
- Initial `anna.storage.get` returned empty: PASS
- Note create used `anna.storage.set`: PASS
- Stored value contained `version`, `nextOrder`, and `notes`: PASS
- Subsequent `anna.storage.get` returned the saved note: PASS
- Summarize re-read storage before invoking the Tool: PASS
- Empty input blocked: PENDING
- Save clears input: PENDING
- Orders 1,2,3 created: PENDING
- Delete persisted through `anna.storage.set`: PENDING
- New note received order 4: PENDING
- iframe reload restored notes through `anna.storage.get`: PENDING
- Summarize called `anna.tools.invoke`: PASS
- Invoke target was `tool-test-mini-notes-summary-12345678` / `summarize_notes`: PASS
- Invoke `args.notes` was an object array: PASS
- RPC no-LLM error `[-32603] manifest 不授予 "LLM.complete"` observed: PASS
- `--no-llm` error displayed: PENDING
- No fallback summary: PASS
- Notes remained usable after Tool error: PENDING

## Evidence files

Attach only screenshots captured during the real browser session:

- `evidence/ui-empty-state.png`
- `evidence/ui-notes-created.png`
- `evidence/ui-note-deleted-and-order-4.png`
- `evidence/ui-no-llm-error.png`

Do not change any item to PASS until that interaction has actually been completed. Source locations may corroborate Host API wiring but do not replace UI interaction evidence.

The observed CLI 0.1.37 RPC error differs from the example `harness started with --no-llm` wording but is recorded as the equivalent disabled-LLM result after a real `anna.tools.invoke`. It must not be “fixed” by calling `anna.llm.complete`, inventing a deterministic summary, or bypassing the Executa over HTTP.

Backend Sampling is independently covered by `npm run executa:mock` and `npm run test:protocol`; the UI tools invocation and its disabled-LLM error are not treated as a mock Sampling result.

## Source corroboration (not UI PASS evidence)

- Runtime connection: `src/anna/runtime.ts:16`
- Storage read: `src/anna/storage.ts:67`
- Storage writes: `src/anna/storage.ts:87` and `src/anna/storage.ts:100`
- Tool invocation: `src/anna/tools.ts:25`
- Summarize handler/loading flow: `src/App.tsx:79` and `src/App.tsx:171`
- Visible error rendering: `src/App.tsx:126`
