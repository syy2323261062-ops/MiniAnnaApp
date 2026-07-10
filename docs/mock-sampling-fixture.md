# Mock Sampling fixture contract

This project was verified against `@anna-ai/cli` **0.1.37**.

## JSONL schema

`anna-app executa dev --mock-sampling <file>` reads one JSON object per line.
Blank lines and lines beginning with `#` are ignored. A malformed JSON line is
also ignored by this CLI version.

Each usable entry contains:

- `ns`: `"sampling"` (the bridge also accepts the legacy `"llm"` namespace).
- `method`: `"createMessage"` for `sampling/createMessage` (legacy fallback:
  `"complete"` when `ns` is `"llm"`).
- `match.contentIncludes` (optional): substring matched against the combined
  system prompt and message text.
- `result`: the mock Sampling result returned to the Executa.

The result used here contains `role`, `content.type`, `content.text`, `model`,
`stopReason`, and `usage`. When `role == "assistant"` and `content` is already
an object, CLI 0.1.37 returns the result without reshaping it.

CLI 0.1.37 selects the first sampling/createMessage-compatible entry. If its
optional `contentIncludes` does not match, it falls back to the first compatible
entry, so this repository keeps one deterministic entry in the fixture.

## Discovery and launcher behavior

With `--dir executas/mini-notes-summary-python`, the CLI reads `executa.json`.
For `type: "python"`, it derives this command:

```text
uv run --project <executa-dir> <first project.scripts key>
```

The first script key is `tool-test-mini-notes-summary-12345678`, matching the
local `tool_id`. `uv` and Python 3.10+ are therefore development prerequisites.

The current `executa dev --help` and `dev --help` expose no recording,
verbose, or trace flag. Protocol recording is provided by
`scripts/protocol_smoke.py` instead.

## Verified command

From the repository root:

```powershell
npm run executa:mock
```

Equivalent expanded command:

```powershell
anna-app executa dev `
  --dir executas/mini-notes-summary-python `
  --mock-sampling fixtures/sampling-summary.jsonl `
  --invoke summarize_notes `
  --args '<notes JSON object>'
```

This fixture targets the reverse `sampling/createMessage` request. It does not
contain a `tools.invoke` result and cannot bypass the Executa.

