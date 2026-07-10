# Executa binary packaging contract

## Sources checked

- The current [Anna Executa distribution reference](https://anna.partners/developers/reference/executa-distribution) defines the archive-root `manifest.json`, canonical platform keys, archive formats, entrypoint lookup, safe extraction, and Unix permission handling.
- The read-only example at `anna-executa-examples-main/examples/multifile-binary/python-pyinstaller-onedir/manifest.json` demonstrates the same `runtime.binary.entrypoint` map and `permissions` shape.
- The remote reference [build-release workflow](https://github.com/whtcjdtc2007/anna-executa-examples/blob/main/.github/workflows/build-release.yml) was reviewed as a historical CI example.
- The current official [GitHub runner-images list](https://github.com/actions/runner-images) maps `macos-15` to the ARM64 macOS 15 image and `macos-15-intel` to the Intel x86-64 image. Retired/deprecated `macos-13` and `macos-14` labels are not used.
- The installed `anna-app` CLI is version 0.1.37. Its `executa` command exposes publish/upload commands but no standalone binary archive validator.

## Two different manifests

The repository-root `manifest.json` is the Anna App manifest. It is never copied into an Executa archive.

Every binary archive instead receives `executas/mini-notes-summary-python/packaging/manifest.template.json` as its own root-level `manifest.json`. That runtime manifest is:

```json
{
  "name": "mini-notes-summary",
  "display_name": "Mini Notes Summary",
  "version": "0.1.0",
  "description": "Summarizes ordered Mini Notes by asking the Anna host to sample an LLM.",
  "runtime": {
    "binary": {
      "entrypoint": {
        "default": "bin/mini-notes-summary",
        "windows-x86_64": "bin/mini-notes-summary.exe"
      },
      "permissions": {
        "bin/mini-notes-summary": "0o755"
      }
    }
  }
}
```

The `name` and `version` exactly match the Executa `describe` manifest. The approved local development `tool_id` remains `tool-test-mini-notes-summary-12345678`; it is not substituted for the runtime manifest name.

For an entrypoint map, the current distribution contract resolves a full platform key first, then an OS key, then `default`. This means Windows selects the `.exe` override while both macOS builds select the default Unix path. The permissions map causes the Unix executable to be restored as mode `0o755`.

## Archive rules

Release filenames are fixed:

- `mini-notes-summary-darwin-arm64.tar.gz`
- `mini-notes-summary-darwin-x86_64.tar.gz`
- `mini-notes-summary-windows-x86_64.zip`

The archive root contains only:

```text
manifest.json
bin/
└── mini-notes-summary[.exe]
```

There is no extra parent directory. Source, tests, fixtures, virtual environments, caches, and PyInstaller work directories are excluded. Zip and tar member paths are rejected if they are absolute, drive-qualified, contain backslashes or `..`, or are links/special files.

`scripts/verify_archive.py` is the project validator for these rules. It performs full structure and manifest checks on every host and runs `scripts/smoke_binary.py` only when the archive platform matches the current host.

## Differences from the references

The read-only example manifest and current official distribution schema agree on the entrypoint map and permission fields. The example includes additional platforms not required by this project.

The remote reference workflow is older and packages bare executables without this project’s archive-root runtime manifest; its Python matrix also does not produce the required Windows Python archive. The project workflow therefore follows the current distribution documentation and performs manifest-aware packaging, native smoke tests, strict verification, artifact aggregation, and a separate Release upload job.

The final build matrix is `macos-15` / `darwin-arm64`, `macos-15-intel` / `darwin-x86_64`, and `windows-latest` / `windows-x86_64`. Each job builds only its native platform and emits the corresponding `.tar.gz` or `.zip` asset.

Because CLI 0.1.37 has no archive validation subcommand, no CLI validation result is claimed for the binary archive. App strict validation remains a separate check, and the archive is validated by the documented project verifier plus native JSON-RPC smoke testing.

PyInstaller is configured as onefile with UPX and stripping disabled. Onefile startup can be slower because it extracts to a temporary directory, so the smoke test permits a bounded 90-second startup/response window while still requiring a clean exit and JSON-only stdout.

The Executa includes the exact repository `executa_sdk/sampling.py` implementation and its MIT license under `executas/mini-notes-summary-python/executa_sdk/`. PyInstaller and uv resolve this local package directly; neither a clean Git checkout nor a target machine depends on the ignored `anna-executa-examples-main` reference directory.
