# Windows binary acceptance evidence

- Build date: `2026-07-11 10:45:36 +08:00`
- Build command: `npm run build:binary`
- Python: `3.12.13`
- PyInstaller: `6.21.0`
- Platform key: `windows-x86_64`
- Executable filename: `mini-notes-summary.exe`
- Executable size: `9,922,097 bytes`
- Executable SHA-256: `c5deb7ffdb7127e7eb52a6951bfb18ec013160214a3a1fb6d8f63a599f974e5e`
- Archive filename: `mini-notes-summary-windows-x86_64.zip`
- Archive size: `9,715,334 bytes`
- Archive SHA-256: `fc853722903b784f72d9ea7b0bc0ea381254591ebe66d144496cda11556f300d`

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
