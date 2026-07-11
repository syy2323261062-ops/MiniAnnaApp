# Windows binary acceptance evidence

- Build date: `2026-07-11 10:03:36 +08:00`
- Build command: `npm run build:binary`
- Python: `3.12.13`
- PyInstaller: `6.21.0`
- Platform key: `windows-x86_64`
- Executable filename: `mini-notes-summary.exe`
- Executable size: `9,923,224 bytes`
- Executable SHA-256: `773b393582200947e91f76e410f70c162adbc9d07d7ebad75c9cc0c20fa8af80`
- Archive filename: `mini-notes-summary-windows-x86_64.zip`
- Archive size: `9,716,186 bytes`
- Archive SHA-256: `4f37083a4875379716eed8d06935fa78cbaf7b36d6d49f63085c97fd0a76ec4f`

## Archive root files

```text
manifest.json
bin/mini-notes-summary.exe
```

## Verification results

- Native binary smoke: `PASS` — initialize, describe, health, and shutdown; four JSON stdout lines; one stderr log line.
- Archive verifier: `PASS` — exact Windows filename/platform, flat root, runtime manifest, `.exe` entrypoint, safe members, expected files only, and native extracted-binary smoke.
- Archive inspector: `PASS` — manifest, entrypoint, sizes, and SHA-256 values above were read from the rebuilt archive.

The generated executable, staging directory, and archive remain under ignored `dist/` paths. This Markdown evidence records the verified metadata without committing generated binaries.
