# CLI 0.1.37 reverse Sampling permission investigation

Status: **CONFIRMED; CLI 0.1.37 compatibility workaround authorized**.

This investigation was read-only until this document was written. In particular, `manifest.json`, the React source, the Executa implementation, and the read-only reference repository were not changed.

## Conclusions

1. An Executa declaring `host_capabilities: ["llm.sample"]` does **not** require, and is not helped by, adding `"llm.complete"` to the App's top-level `permissions` under `@anna-ai/cli` 0.1.37. The relevant ACL does not read that field.
2. In the current runtime, `ui.host_api.llm: ["complete"]` is the only tested App-manifest change that passes this ACL. That field grants the iframe-facing `anna.llm.complete` surface; it is not a Sampling-only installation permission.
3. The intended Mini Notes architecture still uses only `anna.tools.invoke -> Executa -> sampling/createMessage`. For stock CLI 0.1.37, the App additionally declares `ui.host_api.llm.complete` solely as a compatibility ACL so the Executa-originated reverse request can cross the known local-runtime defect.
4. The observed `[-32603] manifest 不授予 "LLM.complete"` occurs after the Executa has emitted `sampling/createMessage`, but before the request reaches the Node LLM bridge and its `--no-llm` rejection. It is an App `ui.host_api` ACL failure caused by reverse Sampling being dispatched through the iframe session.
5. `question.md` forbids a direct frontend `anna.llm.complete` call and requires the path `anna.tools.invoke -> Executa -> sampling/createMessage`; it does not prohibit a manifest ACL declaration. The current stage explicitly authorizes the compatibility grant while requiring an automated no-direct-LLM source check.

## Versions and source inspected

- Installed CLI: `@anna-ai/cli` **0.1.37**, from `node_modules/@anna-ai/cli/package.json`.
- Pinned local runtime: `anna-app-runtime-local` **0.2.0a14**, selected in `node_modules/@anna-ai/cli/dist/bridge-C_Vpmwag.js`.
- App validation ACL mirror: `node_modules/@anna-ai/cli/dist/cli.js`.
- Harness proxy and `--no-llm` bridge: `node_modules/@anna-ai/cli/dist/server-Cg13x19g.js`.
- Pinned Python runtime source in the local uv cache:
  - `dist/uv-cache/archive-v0/RjuYAVTsqR9k_Nwf/anna_app_runtime_local/session.py`
  - `dist/uv-cache/archive-v0/RjuYAVTsqR9k_Nwf/anna_app_runtime_local/store.py`
  - `dist/uv-cache/archive-v0/oYo0vtoku1Ps6Atk/anna_app_core/acl.py`
  - `dist/uv-cache/archive-v0/oYo0vtoku1Ps6Atk/anna_app_core/dispatcher.py`
- Browser SDK namespace construction: `node_modules/@anna-ai/app-runtime/dist/index.js`.
- Project files listed in the stage request, including `question.md`, the App manifest and frontend, and the Executa source.
- Read-only references:
  - `anna-executa-examples-main/examples/anna-app-llm-demo/`
  - `anna-executa-examples-main/examples/python/sampling-summarizer/`

The CLI's minimal App template grants only tools/storage through `ui.host_api`. Its Executa template separately declares `host_capabilities: ["llm.sample"]`. The LLM demo exposes `ui.host_api.llm` because that demo intentionally supports a direct iframe LLM call; that is not the Mini Notes architecture.

## Key implementation findings

### App ACL source

`anna_app_core.acl.host_api_allows` builds the decision from `manifest.ui.host_api`. It does not consult the App's top-level `permissions` and does not consult an App-level `host_capabilities` value.

`anna_app_core.dispatcher.LocalDispatcherSession.call` invokes that ACL and raises `manifest does not grant 'llm.complete'` when `llm.complete` is absent from `ui.host_api`.

The JavaScript strict-validator mirror in `node_modules/@anna-ai/cli/dist/cli.js` follows the same `ui.host_api` rule.

### Reverse Sampling mapping

`anna_app_runtime_local.session.LocalServerRequestHandler` maps Executa reverse RPC method `sampling/createMessage` to dispatcher namespace/method `("llm", "complete")`. It then calls the same `LocalDispatcherSession` used for iframe Host API calls. That re-enters the App's `ui.host_api` ACL even though the request originated from the Executa.

The resulting local-session permission error is converted to JSON-RPC code `-32603` before `anna_app_runtime_local.store` can forward the operation to `host.llm.complete`.

The exact `harness started with --no-llm` error is produced later by the Node LLM bridge in `node_modules/@anna-ai/cli/dist/server-Cg13x19g.js`. The current request never reaches that layer.

### Direct iframe surface

`@anna-ai/app-runtime` constructs an `anna.llm` proxy in the browser SDK. Adding `ui.host_api.llm: ["complete"]` is therefore a real ACL grant, not a Sampling-only protocol field. The compatibility workaround is acceptable here only because the approved project contract separately forbids frontend business code from using it and `scripts/check_no_direct_llm.py` enforces that rule across production `src/` files.

There is also a CLI 0.1.37 harness-specific asymmetry: the Node proxy intercepts iframe `llm.*` calls before the Python ACL path. The current Mini Notes source never makes such a call, but this behavior is another reason not to describe `ui.host_api.llm` as Sampling-only or to rely on this harness version as proof of production permission enforcement.

## Reproduced ACL decision

The pinned runtime's `host_api_allows` function was invoked against four isolated manifest variants:

| Variant | `llm.complete` allowed |
| --- | ---: |
| Current manifest | `False` |
| Add only top-level `permissions: ["llm.complete"]` | `False` |
| Add only App-level `host_capabilities: ["llm.sample"]` | `False` |
| Add `ui.host_api.llm: ["complete"]` | `True` |

This was a direct ACL check, not a sequence of edits to the project manifest.

## Actual failure path

```text
iframe anna.tools.invoke
  -> Node harness proxy
  -> Python LocalDispatcherSession.call("tools", "invoke")
  -> local Executa invoke
  -> Executa emits sampling/createMessage
  -> LocalServerRequestHandler maps it to ("llm", "complete")
  -> same App LocalDispatcherSession.call("llm", "complete")
  -> App ui.host_api ACL rejects the call
  -> LocalSessionError becomes JSON-RPC -32603

The request does not reach:
  -> store delegate host.llm.complete
  -> Node LLM bridge
  -> `--no-llm` rejection
```

Consequently, the previously observed permission text is **not** an equivalent `--no-llm` result. It proves that `anna.tools.invoke` reached the Executa and that the Executa requested reverse Sampling, but it does not prove the final disabled-LLM bridge was reached.

## Preferred upstream fix and local compatibility workaround

The preferred upstream fix belongs in `anna-app-runtime-local` (or a newer CLI that contains the equivalent fix): an Executa-originated `sampling/createMessage` request should be authorized using the Executa's declared `llm.sample` host capability and then forwarded to the host LLM bridge without passing through the App iframe's `ui.host_api.llm` ACL.

That fix must preserve origin separation:

- iframe code remains authorized only for `storage.get`, `storage.set`, and required tools;
- the Executa remains authorized for `llm.sample` through its own manifest/capability negotiation;
- only the Executa-originated reverse request enters the host LLM bridge;
- `src/` continues to contain no direct `anna.llm.complete` call.

Until such a runtime is available, this repository adds `ui.host_api.llm: ["complete"]` as the minimal CLI 0.1.37 compatibility declaration. The top-level App permissions remain unchanged, the Executa capability remains `llm.sample`, and the frontend path remains `anna.tools.invoke` only. This is enforced as a source-code rule rather than described as a mechanism-level inability to access the SDK proxy.

## App-side compatibility decision

The root App manifest now declares `ui.host_api.llm: ["complete"]` for the pinned local runtime only:

- top-level `permissions` does not add `llm.complete`, because it is demonstrably ineffective for this ACL;
- the Executa capability remains `host_capabilities: ["llm.sample"]`;
- production frontend source must contain no direct LLM call;
- no HTTP, fixed-summary, fixture, or fallback bypass is introduced;
- `scripts/check_no_direct_llm.py` and `scripts/check_identity.py` enforce the frontend and identity contracts.

This workaround should be reevaluated when the project upgrades to a runtime that authorizes Executa reverse Sampling by origin and capability.
