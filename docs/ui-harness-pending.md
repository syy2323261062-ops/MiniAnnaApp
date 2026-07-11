# UI harness manual acceptance pending

Status: **PARTIALLY COMPLETE**. Core question.md UI/Host API behavior, absence of a fallback summary, the real no-LLM bridge path, and all four repository screenshots are complete. Only a reliably observed loading transition remains `NOT RUN` because it completed too quickly to verify visually.

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

The real session verified storage CRUD, blank-input rejection, input clearing, ordered notes, deletion, iframe-lifecycle restoration, `tools.invoke`, the reverse request reaching the explicit `--no-llm` bridge, and working create/delete operations after the error. The sanitized combined recording is `evidence/ui-no-llm-rpc.jsonl`.

Still required before this document can be marked resolved:

- optionally repeat Summarize with throttling or video if visual evidence of the very short `Working…` transition is desired.

No item is marked PASS from source inspection alone.
