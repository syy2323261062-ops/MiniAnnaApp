# UI Harness Verification

- Date: 2026-07-11
- CLI version: 0.1.37
- Command: `npm run dev:anna:no-llm`
- Browser: PENDING
- Harness URL: `http://localhost:5180/`

## Required by question.md

- App loaded and runtime connected: PENDING
- Initial empty state displayed: PENDING
- Empty, whitespace-only, and newline-only input blocked: PENDING
- Save clears input: PENDING
- `anna.storage.get` used: PENDING
- `anna.storage.set` used: PENDING
- Notes display content and order: PENDING
- Delete persisted and removed the note: PENDING
- App iframe refresh restored current lifecycle state: PENDING
- Summarize re-read current notes: PENDING
- `anna.tools.invoke` used with `summarize_notes`: PENDING
- Executa emitted `sampling/createMessage`: PENDING
- Reverse request reached the CLI `--no-llm` bridge: PENDING
- Real `--no-llm` error displayed: PENDING
- No fallback summary displayed: PENDING
- Notes CRUD remained usable after the error: PENDING

## Additional quality checks

- Versioned storage value contains `version`, `nextOrder`, and `notes`: PENDING
- `nextOrder` is monotonic after deletion: PENDING
- Deleted order is not reused: PENDING
- Four required UI screenshots captured: PENDING
- UI RPC log captured: PENDING
- Windows binary SHA recorded separately: PASS
- Protocol recording exists: PASS

## Evidence files

- `evidence/ui-empty-state.png`
- `evidence/ui-notes-created.png`
- `evidence/ui-note-deleted.png`
- `evidence/ui-no-llm-error.png`
- `evidence/ui-no-llm-rpc.log`

Only results observed in the real browser/RPC session may be marked PASS. The compatibility declaration in `manifest.json` does not count as UI evidence. Backend Sampling remains independently covered by `npm run executa:mock` and `npm run test:protocol`.
