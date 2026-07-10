# UI harness manual acceptance pending

This item is not complete. It must be repeated during final acceptance in an environment that permits local browser control and interaction with the Anna App harness.

## Expected command

```powershell
npm run build
npm run dev:anna:no-llm
```

## Verified from actual CLI 0.1.37 RPC logs

- Runtime connected and initial `anna.storage.get` returned empty.
- Creating a note called `anna.storage.set` with `version`, `nextOrder`, and `notes`.
- A later `anna.storage.get` returned the saved note.
- Summarize re-read storage and invoked `tool-test-mini-notes-summary-12345678` method `summarize_notes` with an object-array `args.notes`.
- The actual disabled-LLM result was `[-32603] manifest 不授予 "LLM.complete"`.
- No fallback summary was generated.

The error text is the current CLI environment’s equivalent no-LLM result. It must not be removed by adding `anna.llm.complete`, a fixed summary, a custom HTTP service, or a UI fixture. Backend Sampling already passes the separate mock-Sampling CLI and protocol smoke tests.

## Manual UI steps still required

1. Confirm the page title, empty state, input, and Save button visually.
2. Confirm empty, whitespace-only, and newline-only inputs cannot be saved.
3. Create three notes and visually confirm orders 1, 2, and 3 plus input clearing.
4. Delete order 2, add another note, and confirm it receives order 4.
5. Reload only the App iframe and visually confirm storage restoration.
6. Confirm Summarize loading state and visible rendering of the actual error.
7. Confirm notes remain usable after the Tool error.
8. Capture the four named UI evidence screenshots.

## Current blocker

The prior environment did not grant the sandbox/browser control needed to complete reliable manual harness interaction. Repeated browser attempts are intentionally deferred; no process ID is recorded because process identifiers are transient and may be reused.

Final acceptance must run and record these steps before the UI harness item can be marked complete.
