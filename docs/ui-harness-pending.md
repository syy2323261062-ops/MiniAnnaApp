# UI harness manual acceptance pending

Status: **PENDING** until a clean CLI 0.1.37 browser session completes the checklist and writes real evidence.

## Compatibility prerequisite

The pinned local runtime maps Executa `sampling/createMessage` to an internal `llm.complete` dispatcher call and sends that reverse request through the App `ui.host_api` ACL. The root manifest now declares `ui.host_api.llm.complete` as a local harness compatibility workaround.

The Mini Notes frontend must still use only:

```text
anna.tools.invoke
  -> Executa summarize_notes
  -> sampling/createMessage
```

`npm run check:no-direct-llm` enforces that no production `src/` file directly calls the LLM API.

## Required run

```powershell
npm run build
npm run dev:anna:no-llm
```

The real session must verify storage CRUD, blank-input rejection, input clearing, ordered notes, deletion, iframe-lifecycle restoration, Summarize loading, `tools.invoke`, `sampling/createMessage`, an explicit `--no-llm` bridge error, no fallback summary, and working CRUD after the error.

Evidence must be saved to the five paths listed in `evidence/ui-harness-checklist.md`. No item may be marked PASS from source inspection alone.
