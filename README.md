# Mini Notes with LLM Summary

## 1. Project Overview

Mini Notes is a local Anna App for creating, viewing, deleting, and summarizing ordered notes. Notes are stored exclusively through the Anna storage Host API. Summaries are requested from the bundled `mini-notes-summary` Executa, which uses reverse JSON-RPC Sampling rather than a frontend LLM call or a deterministic fallback.

The fixed project identities are:

```text
App slug: mini-notes
Executa handle: mini-notes-summary
Bundled reference: bundled:mini-notes-summary
Local tool_id: tool-test-mini-notes-summary-12345678
Tool method: summarize_notes
Storage key: mini-notes:notes:v1
Version: 0.1.0
```

Local development does not require `anna-app login`, an Anna account, an API key, or a real LLM.

## 2. Architecture

```text
React UI in Anna iframe
  → AnnaAppRuntime.connect()
  → anna.storage.get/set
  → anna.tools.invoke(method: summarize_notes)
  → local Mini Notes Summary Executa
  → JSON-RPC sampling/createMessage
  → host LLM bridge or offline mock fixture
  → summary result returned to the UI
```

- `manifest.json` describes Anna App permissions, UI bundle/views, Host APIs, and the required bundled Executa.
- `bundle/` is the React/Vite static output loaded in the Anna iframe.
- `executas/` contains the local Executa source, manifest, tests, and launcher configuration.
- `anna.storage.*` is the App iframe’s APS KV/legacy runtime-state Host API. React state is only a rendering cache.
- `anna.tools.invoke` is the Host API path from the iframe to the Executa.
- `sampling/createMessage` is reverse JSON-RPC through which the Executa borrows the host LLM.
- A binary archive is a standalone publishable Executa artifact that does not require Python, uv, executa-sdk, or project source on the target machine.

## 3. Project Structure

```text
manifest.json                         Anna App manifest
app.json                              App metadata and bundled Executa path
src/                                  React + TypeScript source
src/anna/runtime.ts                   Anna runtime connection
src/anna/storage.ts                   versioned storage CRUD and nextOrder
src/anna/tools.ts                     anna.tools.invoke wiring
bundle/                               generated Vite static bundle
executas/mini-notes-summary-python/   Python Executa source and tests
executas/.../executa_sdk/             vendored repository SamplingClient + MIT license
fixtures/sampling-summary.jsonl       offline Sampling fixture
scripts/                              identity, protocol, binary and CI checks
evidence/                             protocol and UI acceptance evidence
docs/                                 packaging and test notes
docs/acceptance-matrix.md             question.md requirement-by-requirement status
.github/workflows/release.yml         three-platform Release workflow
```

`anna-executa-examples-main/` is read-only reference material and is not part of the final application source or release archive.

## 4. Prerequisites

- Node.js 22 or newer and npm.
- `uv` available on `PATH`.
- Python 3.10 or newer for the SDK; Python 3.12 is pinned and recommended for tests and binary builds.
- Installed Anna CLI comes from the npm development dependencies; the locally verified version is 0.1.37.

## 5. Install Dependencies

The committed lock file pins `@anna-ai/cli` exactly to 0.1.37 and uses the official npm registry. Install the reproducible dependency set with:

```powershell
npm ci
```

Use `npm install` only when intentionally updating the lock file.

If the first harness startup must create its Python environment and exceeds the CLI startup window, pre-warm only the project Executa environment:

```powershell
uv sync --python 3.12 --project executas/mini-notes-summary-python
```

## 6. Build the UI Bundle

```powershell
npm run build
```

Vite uses `base: "./"` and writes the build to the repository-root `bundle/`. The repository can regenerate this directory after dependency installation; stale output must not be mixed with newer source.

## 7. Strict Manifest Validation

```powershell
npm run validate
```

This runs `anna-app validate --strict` against the App manifest. It is separate from Executa binary archive verification.

## 8. Run UI Harness with `--no-llm`

```powershell
npm run dev:anna:no-llm
```

Open the local URL printed by the CLI. This starts the default legacy in-memory storage harness and the bundled local Executa without using an Anna login or a real LLM.

CLI 0.1.37 pins `anna-app-runtime-local` 0.2.0a14. That runtime maps an Executa reverse `sampling/createMessage` request to an internal `llm.complete` dispatcher call and incorrectly sends it through the App `ui.host_api` ACL. The manifest therefore declares `ui.host_api.llm.complete` as a stock-CLI compatibility workaround. Mini Notes production frontend source must not call that API; enforce this separately with:

```powershell
npm run check:no-direct-llm
```

The required browser acceptance checklist is in `evidence/ui-harness-checklist.md`. Do not mark it PASS without completing the real interactions.

Start dashboard recording before the UI interactions, but keep the raw download outside the repository (or under ignored `evidence/raw/`). Sanitize it before adding evidence:

```powershell
uv run --python 3.12 python scripts/sanitize_ui_rpc_log.py `
  <raw-dashboard-recording.jsonl> `
  evidence/ui-no-llm-rpc.jsonl

npm run test:sanitize
```

The sanitizer removes `auth.refresh` records, redacts nested credentials/token fields and JWT/Bearer values, and refuses to overwrite its input.

## 9. Test Notes CRUD

In the running UI harness:

1. Confirm empty, whitespace-only, and newline-only input cannot be saved.
2. Create `明天跟客户 follow up`, `修复登录 bug`, and `Workshop 内容想法`; orders must be 1, 2, and 3, and the input must clear after each save.
3. Delete order 2 and confirm orders 1 and 3 remain.
4. Create `整理项目 README`; its order must be 4 because persisted `nextOrder` is never reused.
5. Reload only the App iframe and confirm the notes are restored through `anna.storage.get` within the same harness lifecycle.

The storage value has this versioned shape:

```json
{
  "version": 1,
  "nextOrder": 4,
  "notes": []
}
```

The app does not use localStorage, IndexedDB, a filesystem, or a custom HTTP API.

## 10. Why Summarize Fails under `--no-llm`

The frontend always calls `anna.tools.invoke`; it does not call `anna.llm.complete`. The expected local path is:

```text
anna.tools.invoke
  -> Mini Notes Summary Executa
  -> sampling/createMessage
  -> CLI no-LLM bridge
  -> harness started with --no-llm
```

CLI 0.1.37's pinned runtime incorrectly applies the App iframe ACL to the internal `llm.complete` dispatcher call used for reverse Sampling. `ui.host_api.llm.complete` is declared only to let that Executa-originated request cross the stock local runtime. It is not used by frontend business code, and `scripts/check_no_direct_llm.py` fails if a direct call is introduced under `src/`.

The earlier `manifest 不授予 "LLM.complete"` result was a permission-stage failure, not an equivalent `--no-llm` result. With the compatibility ACL in place, the harness must instead return an error explicitly caused by `--no-llm`. It must not be hidden by a fixed summary, HTTP fallback, or UI fixture.

Backend reverse Sampling is independently verified by `npm run executa:mock` (`anna-app executa dev --mock-sampling`) and `npm run test:protocol` (`protocol_smoke.py`), both without a real LLM.

## 11. Test Executa with `--mock-sampling`

```powershell
npm run executa:mock
```

This invokes `summarize_notes` through `anna-app executa dev` and serves the reverse Sampling response from `fixtures/sampling-summary.jsonl`. It does not call a real model. A successful result proves that the Executa emitted `sampling/createMessage` and consumed the matching mock response.

Run the complete Executa pytest suite with:

```powershell
npm run test:executa
```

## 12. Manual JSON-RPC Tests

The reproducible protocol driver sends `initialize`, `describe`, `health`, `invoke`, a reverse Sampling response, and `shutdown` over newline-delimited JSON-RPC stdio:

```powershell
npm run test:protocol
```

It verifies protocol 2.0 negotiation, `client_capabilities.sampling = {}`, `llm.sample`, the `summarize_notes` tool, reverse response dispatch, and JSON-only stdout.

## 13. Protocol Evidence

`npm run test:protocol` records the frame sequence at:

```text
evidence/protocol-smoke.jsonl
```

Each line names the direction/event and includes the JSON-RPC frame. The offline fixture contract is documented in `docs/mock-sampling-fixture.md`.

## 14. Verify `anna.storage.get/set`

Production storage calls are implemented in `src/anna/storage.ts`:

- load uses `anna.storage.get({ key: "mini-notes:notes:v1" })`;
- create and delete write the complete versioned value with `anna.storage.set`;
- `nextOrder` is persisted independently of the current notes, preventing deleted orders from being reused.

The UI loads storage on connection and refreshes rendering state only after Host API operations complete.

## 15. Verify `tools.invoke → Executa → sampling/createMessage`

`src/anna/tools.ts` calls the bundled reference with method `summarize_notes`. `executa_manifest.py` exposes the same method and declares `host_capabilities: ["llm.sample"]`. `mini_notes_summary.py` builds the note prompt, calls the exact vendored copy of the repository `SamplingClient`, dispatches the reverse response through the shared stdin reader, and returns only the sampled text. The vendored SDK files retain Anna’s MIT license and remove any clean-checkout dependency on the ignored reference repository.

Run these checks together:

```powershell
npm run check:identity
npm run check:no-direct-llm
npm run test:executa
npm run test:protocol
npm run executa:mock
```

## 16. Build the Native Binary

Build the current native platform with Python 3.12 and PyInstaller onefile:

```powershell
npm run build:binary
```

Or require the current Windows x86-64 host explicitly:

```powershell
uv run --python 3.12 python scripts/build_binary.py `
  --platform windows-x86_64
```

The script rejects platform keys that do not match the host. Windows uses neither stripping nor UPX. Build work, staging, and release output are kept under ignored `dist/` paths.

## 17. Archive Structure

Windows archive root:

```text
manifest.json
bin/
└── mini-notes-summary.exe
```

macOS archive root replaces the entrypoint with executable `bin/mini-notes-summary` and declares permission `0o755`. No source, tests, fixture, virtual environment, cache, or extra parent directory is included.

The archive runtime manifest is distinct from the repository-root Anna App manifest. Its entrypoint map selects the Windows `.exe` override and the default Unix path.

## 18. Verify and Inspect an Archive

```powershell
uv run --python 3.12 python scripts/verify_archive.py `
  dist/release/mini-notes-summary-windows-x86_64.zip

uv run --python 3.12 python scripts/inspect_archive.py `
  dist/release/mini-notes-summary-windows-x86_64.zip
```

The verifier checks the exact filename/platform, safe paths, flat root, manifest identity/version, entrypoint, extension, permissions, unexpected files, and native smoke when the archive matches the host. The inspector makes no changes and prints paths, manifest, sizes, and SHA-256 hashes.

## 19. GitHub Actions Release

`.github/workflows/release.yml` supports:

- `push` of a `v*` tag, publishing to `github.ref_name`;
- `workflow_dispatch` with required prerelease `release_tag`, for example `v0.1.0-rc.1`.

The native matrix is:

| Runner | Platform | Archive format |
|---|---|---|
| `macos-15` | `darwin-arm64` | `tar.gz` |
| `macos-15-intel` | `darwin-x86_64` | `tar.gz` |
| `windows-latest` | `windows-x86_64` | `zip` |

The independent `validate-app` job uses Node.js 22, Python 3.12, `npm ci`, the frontend build, strict App validation, identity/no-direct-LLM checks, sanitizer tests, protocol smoke, and CLI mock Sampling. Every native build job depends on that job, then runs pytest, identity checks, PyInstaller, native binary smoke, and archive verification. The Release job waits for the complete matrix, downloads all artifacts, requires exactly three filenames, and only then creates or updates the Release.

Workflow artifacts are intermediate CI outputs. Release assets are the three archives uploaded by the final Release job. Check workflow structure locally with:

```powershell
npm run check:workflow
```

This is a YAML/static contract check, not evidence that GitHub-hosted jobs have run.

## 20. Expected Release Assets

```text
mini-notes-summary-darwin-arm64.tar.gz
mini-notes-summary-darwin-x86_64.tar.gz
mini-notes-summary-windows-x86_64.zip
```

A real RC run should retain the Release and record its run URL, tag, three job results, and all asset SHA-256 values.

## 21. Limitations

- Legacy harness storage persists only within the running local harness lifecycle; restarting `anna-app dev` is not required to preserve data.
- The `--no-llm` harness intentionally cannot return a sampled summary; backend Sampling is tested with the mock fixture instead.
- UI acceptance remains pending until the browser checklist is actually completed and screenshots are captured.
- `docs/acceptance-matrix.md` distinguishes PASS, FAIL, BLOCKED, and NOT RUN; source presence alone is not UI evidence.
- Local Windows native build and archive verification do not prove macOS builds.
- Workflow static validation does not prove a real GitHub Actions run or Release upload.
- No commit, push, workflow dispatch, tag, or Release operation should be performed without explicit user authorization and authenticated GitHub access.
