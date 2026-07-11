# Mini Notes with LLM Summary

[English](README.md) | 简体中文

## 1. 项目简介

Mini Notes 是一个本地运行的 Anna App。用户可以创建、查看、删除按顺序编号的笔记，并通过本地 Executa 请求摘要。

笔记的唯一事实来源是 Anna storage Host API：创建、读取和删除都必须经过 `anna.storage.get` / `anna.storage.set`。React state 只用于界面渲染，不作为持久化来源。前端点击 Summarize 后必须调用 `anna.tools.invoke`；`mini-notes-summary` Executa 再通过 reverse JSON-RPC `sampling/createMessage` 向 Host LLM 或本地 mock Sampling 请求摘要。

生产前端不直接调用 `anna.llm.complete`，项目也不使用自建 HTTP API、`localStorage`、IndexedDB、文件系统存储或规则/固定文本伪造 summary。本地开发与验收不需要 Anna 账号、`anna-app login`、真实 LLM 或真实 API key。

## 2. 核心架构

```text
Anna iframe
  -> AnnaAppRuntime.connect()
  -> anna.storage.get/set
  -> anna.tools.invoke
  -> Mini Notes Summary Executa
  -> sampling/createMessage
  -> Host LLM 或 mock Sampling
  -> summary 返回 UI
```

- `manifest.json` 声明 App bundle、view、Host API 权限和所需的 bundled Executa。
- App iframe 通过 Anna App Runtime 连接本地 harness。
- storage Host API 保存带版本号和 `nextOrder` 的完整 notes 对象。
- `anna.tools.invoke` 是 iframe 到 Executa 的唯一摘要调用入口。
- Executa 使用 JSON-RPC 2.0 over stdio，并通过 reverse Sampling 借用 Host LLM 能力。
- binary archive 是可独立分发的 Executa 产物，目标机器不需要 Python、uv、executa-sdk 或项目源码。

## 3. 固定身份

以下值是跨 App、前端、Executa、fixture、测试、打包和 workflow 的统一契约，不应单独修改：

```text
App slug: mini-notes
Executa handle: mini-notes-summary
Bundled reference: bundled:mini-notes-summary
Local tool_id: tool-test-mini-notes-summary-12345678
Tool method: summarize_notes
Storage key: mini-notes:notes:v1
Version: 0.1.0
```

## 4. 项目目录结构

```text
app.json                              App 元数据和 bundled Executa 路径
manifest.json                         Anna App manifest
src/                                  React + TypeScript 源码
src/anna/                             runtime、storage、tools 和类型封装
public/anna-tool-ids.js               本地 harness tool_id 常量
bundle/                               Vite 构建产物（不提交）
executas/mini-notes-summary-python/   Python Executa、测试和打包配置
executas/.../executa_sdk/             vendored SamplingClient 与许可证
fixtures/sampling-summary.jsonl       离线 mock Sampling fixture
scripts/                              协议、身份、脱敏、二进制和 CI 检查
docs/                                 架构、打包与验收文档
evidence/                             可提交的脱敏验收证据
.github/workflows/release.yml         三平台 Release workflow
question.md                           原始题目与验收要求
```

`bundle/` 是可再生成的前端构建产物，`dist/` 是本机二进制构建产物，两者都不提交。`anna-executa-examples-main/` 仅为本机只读参考，不属于最终项目。`executas/.../executa_sdk/` 是项目实际依赖的 vendored SDK，保留了相应许可证，因此从 GitHub 全新克隆后不依赖被忽略的参考目录。

## 5. 从全新电脑开始配置环境

通用前置条件：

- Git；
- Node.js 22 或更高版本和 npm；
- uv；
- 能访问 GitHub、npm 官方 registry 和 Python 包源的网络。

Windows 推荐步骤：

1. 安装 Git for Windows。
2. 使用 fnm 或 Node.js 官方安装器安装 Node.js 22。
3. 按 uv 官方安装方式安装 uv。
4. 重新打开 PowerShell，让新安装的命令进入 `PATH`。
5. 执行下列版本检查。

macOS/Linux 推荐步骤：

1. 使用系统包管理器或官方安装器安装 Git。
2. 使用 fnm、系统包管理器或 Node.js 官方安装器安装 Node.js 22。
3. 按 uv 官方安装方式安装 uv。
4. 重新打开终端并执行下列版本检查。

```powershell
git --version
node --version
npm --version
uv --version
```

推荐由 uv 安装并管理 Python 3.12：

```powershell
uv python install 3.12
uv python list
```

Anna CLI 不需要全局安装。`package-lock.json` 会安装项目本地、精确固定的 `@anna-ai/cli` 0.1.37。完成本地开发、mock 测试和二进制验收不需要 `anna-app login`、Anna 账号或真实 LLM API key。

## 6. 从 GitHub 克隆

```powershell
git clone https://github.com/syy2323261062-ops/MiniAnnaApp.git
cd MiniAnnaApp
git branch --show-current
git log -1 --oneline
```

正常情况下当前分支应为 `main`。在开始验收前，应确认克隆来源和目标 commit 与预期远端 `main` 一致。

## 7. 安装依赖

优先使用 lock file 进行可复现安装：

```powershell
npm ci
```

仓库已提交 `package-lock.json`，`@anna-ai/cli` 精确固定为 0.1.37，并使用 npm 官方 registry。只有在主动更新依赖和 lock file 时才使用 `npm install`。

首次启动 Executa 时，uv 可能需要创建 Python 环境。若首次 harness 启动因下载或建环境较慢而超时，可先预热项目自己的 Executa 环境：

```powershell
uv sync --python 3.12 --project executas/mini-notes-summary-python
```

## 8. 一键式验收命令顺序

在全新克隆中按以下顺序执行：

```powershell
npm ci
npm run build
npm run validate
npm run check:identity
npm run check:no-direct-llm
npm run test:sanitize
npm run test:executa
npm run test:protocol
npm run executa:mock
npm run check:workflow
npm run build:binary
```

- `npm ci`：从 lock file 安装完全一致的 npm 依赖。
- `npm run build`：类型检查并生成 Anna 可加载的静态 bundle。
- `npm run validate`：执行 App manifest strict validation。
- `npm run check:identity`：检查 App、Executa、fixture、前端和打包身份是否统一。
- `npm run check:no-direct-llm`：阻止 `src/` 直接调用 `anna.llm.complete`。
- `npm run test:sanitize`：验证 UI RPC 日志脱敏器。
- `npm run test:executa`：运行 Executa pytest 协议与错误处理测试。
- `npm run test:protocol`：执行完整离线 JSON-RPC/reverse Sampling smoke。
- `npm run executa:mock`：通过 Anna CLI 和 fixture 验证 mock Sampling 集成。
- `npm run check:workflow`：静态验证 runner、matrix、smoke 和 Release upload 约定。
- `npm run build:binary`：为当前宿主平台构建 PyInstaller onefile 和 archive，并执行验证。

## 9. 构建前端

```powershell
npm run build
```

前端使用 React、TypeScript 和 Vite。`vite.config.ts` 设置 `base: "./"`，因此构建产物适合从 Anna iframe 的相对路径加载。构建会生成：

```text
bundle/index.html
bundle/assets/...
bundle/anna-tool-ids.js
```

`bundle/` 被 Git 忽略；在全新克隆中必须通过上述命令重新生成，不应复用旧工作区的产物。

## 10. strict validation

```powershell
npm run validate
```

该命令等价于项目本地 CLI 的：

```powershell
anna-app validate --strict
```

它会验证 App `manifest.json`、bundle 入口、view、Host API 声明、required Executa 以及 tools/storage 权限。App 根目录 manifest 与 Executa binary archive 根目录的 `manifest.json` 是两个不同 schema，不能互换。

## 11. 启动 UI harness

```powershell
npm run dev:anna:no-llm
```

打开：

```text
http://localhost:5180/
```

该流程不登录 Anna，不调用真实 LLM，使用 CLI 的 legacy in-memory runtime state。外层 dashboard 进程重启后不保证保留 notes；但在同一个 harness 生命周期内，仅刷新 App iframe 应重新调用 `anna.storage.get` 并恢复当前 notes。

## 12. UI 手动验收步骤

1. 分别尝试保存空字符串、只有空格、只有换行的内容，确认均不能创建笔记。
2. 依次创建三条笔记，确认 order 为 1、2、3，并确认每次保存后输入框清空。
3. 删除 order 2，再创建新笔记，确认新 order 为 4，而不是复用 2。
4. 只刷新 App iframe，确认 order 1、3、4 通过 `anna.storage.get` 恢复。
5. 点击 Summarize，确认 RPC 经过 `tools.invoke`，method 为 `summarize_notes`。
6. 在 `--no-llm` harness 中确认最终显示：

   ```text
   [-32603] harness started with --no-llm
   ```

7. 确认 Tool 错误后 Notes CRUD 仍正常，并且页面没有生成任何 fallback summary。

如 dashboard 没有 iframe 刷新按钮，可在 dashboard 顶层 DevTools Console 执行：

```javascript
document.getElementById("app").contentWindow.location.reload()
```

不要用 `Ctrl+R` 刷新整个 dashboard，因为这会重建外层 in-memory runtime state。完整的真实 UI 结果见 [UI harness checklist](evidence/ui-harness-checklist.md)。非常短的 `Working…` 过渡未被可靠观察到，仅作为附加观察记录，不是 `question.md` 的独立硬性验收项。

## 13. CLI 0.1.37 compatibility workaround

Executa 正确声明 `host_capabilities: ["llm.sample"]`，并发出 reverse `sampling/createMessage`。但 CLI 0.1.37 固定的本地 runtime 会把该 reverse Sampling 映射成内部 `llm.complete` dispatcher 调用，而且会错误地让内部调用经过 App 的 `ui.host_api` ACL。

因此 `manifest.json` 中的 `ui.host_api.llm.complete` 是 CLI 0.1.37 的临时兼容声明。它是实际 iframe ACL，不是 Sampling 专用权限，也不代表前端可以用它完成摘要。生产 `src/` 仍禁止直接调用 `anna.llm.complete`，并由以下命令强制检查：

```powershell
npm run check:no-direct-llm
```

未来 runtime 修复后，应重新评估并移除该兼容项。在当前版本下，缺少它会先得到 `manifest 不授予 "LLM.complete"`；声明兼容 ACL 后，reverse Sampling 才能到达真正的 `--no-llm` bridge，并返回预期错误。

## 14. 后端 mock Sampling

```powershell
npm run executa:mock
```

该命令使用 [fixtures/sampling-summary.jsonl](fixtures/sampling-summary.jsonl)，通过 `anna-app executa dev --mock-sampling` 调用 `summarize_notes`。它验证：

- Executa 收到 `invoke`；
- Executa 发出 `sampling/createMessage`；
- fixture 返回匹配的 mock response；
- summary 只来自 Sampling response，而不是前端或 Tool 的本地规则。

该流程完全离线，不调用真实模型。Executa pytest 套件可单独运行：

```powershell
npm run test:executa
```

## 15. JSON-RPC 协议测试

```powershell
npm run test:protocol
```

协议 driver 通过换行分隔的 JSON-RPC stdio 覆盖：

- `initialize` 与 protocol v2；
- `client_capabilities.sampling = {}`；
- `describe`、`health` 和 `invoke`；
- `host_capabilities` 中的 `llm.sample`；
- `summarize_notes` tool；
- reverse `sampling/createMessage` response dispatch；
- `shutdown`；
- stdout 每个非空行都是 JSON，日志只写 stderr。

可审阅证据位于 [evidence/protocol-smoke.jsonl](evidence/protocol-smoke.jsonl)。

## 16. UI RPC 脱敏

原始 dashboard recording 可能包含认证刷新帧或临时 credential，不能直接提交。将原始文件保存在仓库外，或放到被忽略的 `harness/` / `evidence/raw/`，再执行：

```powershell
uv run --python 3.12 python scripts/sanitize_ui_rpc_log.py `
  <原始-recording.jsonl> `
  evidence/ui-no-llm-rpc.jsonl

npm run test:sanitize
```

脱敏器会移除 `auth.refresh`，递归替换 token、JWT、authorization、cookie 等敏感值，并拒绝覆盖输入文件。可提交的 UI RPC 证据是 [evidence/ui-no-llm-rpc.jsonl](evidence/ui-no-llm-rpc.jsonl)，不是原始 recording。

## 17. Executa 二进制打包

为当前原生平台使用 Python 3.12 和 PyInstaller onefile 构建：

```powershell
npm run build:binary
```

Windows x86-64 也可显式执行：

```powershell
uv run --python 3.12 python scripts/build_binary.py `
  --platform windows-x86_64
```

脚本只允许构建与当前宿主匹配的平台，不进行伪交叉编译。Windows 输出为：

```text
dist/release/mini-notes-summary-windows-x86_64.zip
```

archive 解压后的根目录必须直接是：

```text
manifest.json
bin/mini-notes-summary.exe
```

macOS archive 使用 `bin/mini-notes-summary` 并在 manifest 中声明 `0o755`。目标机器运行 archive 中的 Executa 不需要 Python、uv 或项目源码。

## 18. Archive 验证

Windows 示例：

```powershell
uv run --python 3.12 python scripts/verify_archive.py `
  dist/release/mini-notes-summary-windows-x86_64.zip

uv run --python 3.12 python scripts/inspect_archive.py `
  dist/release/mini-notes-summary-windows-x86_64.zip
```

verifier 检查精确文件名和 platform key、archive root、manifest 身份/版本、entrypoint、Windows/macOS 扩展名、Unix 权限声明、路径穿越、多余父目录和禁止文件；本机平台还会运行 native binary smoke。inspector 是只读脚本，输出 archive 路径、格式化 manifest、entrypoint、文件大小和 SHA-256。

## 19. GitHub Actions

[.github/workflows/release.yml](.github/workflows/release.yml) 支持手动 `workflow_dispatch` 和 `v*` tag。独立的 `validate-app` job 在 Ubuntu 上执行 Node.js 22、Python 3.12、`npm ci`、前端构建、strict validation、身份/禁用直连 LLM 检查、sanitizer、protocol smoke 和 mock Sampling。

原生构建矩阵为：

| Runner | Platform | 格式 |
|---|---|---|
| `macos-15` | `darwin-arm64` | `.tar.gz` |
| `macos-15-intel` | `darwin-x86_64` | `.tar.gz` |
| `windows-latest` | `windows-x86_64` | `.zip` |

每个 build job 都运行 Executa pytest、identity check、PyInstaller 构建、native smoke 和 archive verification。最终 Release job 等待全部矩阵成功，要求恰好三个归档，再上传到 GitHub Release。

期望的 Release assets 是：

```text
mini-notes-summary-darwin-arm64.tar.gz
mini-notes-summary-darwin-x86_64.tar.gz
mini-notes-summary-windows-x86_64.zip
```

workflow artifact 是 job 间传递和下载的中间产物；GitHub Release asset 是最终 Release 页面上可下载的交付物，前者不能替代后者。静态检查命令是：

```powershell
npm run check:workflow
```

## 20. 已有验收证据

- [evidence/ui-empty-state.png](evidence/ui-empty-state.png)
- [evidence/ui-notes-created.png](evidence/ui-notes-created.png)
- [evidence/ui-note-deleted.png](evidence/ui-note-deleted.png)
- [evidence/ui-no-llm-error.png](evidence/ui-no-llm-error.png)
- [evidence/ui-no-llm-rpc.jsonl](evidence/ui-no-llm-rpc.jsonl)
- [evidence/protocol-smoke.jsonl](evidence/protocol-smoke.jsonl)
- [evidence/binary-windows.md](evidence/binary-windows.md)
- [docs/acceptance-matrix.md](docs/acceptance-matrix.md)

这些证据分别覆盖真实 UI、storage CRUD、正确 Tool wiring、no-LLM 错误、无 fallback summary、协议帧、本机 Windows 二进制和逐项验收状态。原始 recording 不属于可提交证据。

## 21. 常见问题

- **Node 低于 22**：升级到 Node.js 22 后删除本机旧依赖并重新执行 `npm ci`。
- **找不到 `uv`**：完成 uv 安装后重开 PowerShell/终端，确认 `uv --version` 可用。
- **`npm ci` 失败**：确认在仓库根目录、lock file 未被手工改坏，并可访问 npm 官方 registry；不要复制另一个工作区的 `node_modules`。
- **端口 5180 被占用**：先确认并停止当前项目自己的旧 harness 进程，再重新启动；不要盲目结束无关进程。
- **Python bridge 首次启动超时**：先执行 `uv sync --python 3.12 --project executas/mini-notes-summary-python` 预热环境。
- **`manifest does not grant llm.complete` / `manifest 不授予 "LLM.complete"`**：这是 CLI 0.1.37 reverse Sampling 被错误送入 App ACL 的权限阶段阻断；确认兼容声明仍在，并运行 `npm run check:no-direct-llm` 保证前端没有直接调用。
- **出现 `[-32603] harness started with --no-llm`**：这是 `--no-llm` UI harness 的预期行为，说明 Tool 路由到达 no-LLM bridge；后端 Sampling 成功由 `executa:mock` 和 `test:protocol` 独立证明。
- **刷新后 notes 丢失**：只能刷新 App iframe；刷新整个 dashboard 或重启 harness 会重建 legacy in-memory runtime state。
- **Windows 无法构建 macOS binary**：PyInstaller 不支持该项目的跨平台伪构建，macOS 两种架构必须在对应 GitHub-hosted macOS runner 上真实构建。
- **Git 中没有 `bundle/`**：这是正常行为；先执行 `npm ci` 和 `npm run build` 生成。

## 22. 安全说明

- 不提交 token、PAT、credential、cookie、Authorization header 或真实 API key。
- 不在源码、fixture 或文档中保存密钥。
- 不提交原始 dashboard recording；只提交经过脚本脱敏且复核后的证据。
- 不提交 `node_modules/`、`bundle/`、`dist/`、`.venv/`、`harness/` 或 `evidence/raw/`。
- 不把本机只读参考目录 `anna-executa-examples-main/` 纳入 Git。
- workflow 和本地测试都不需要 Anna 登录或真实 LLM credential。

## 23. 当前限制

- `--no-llm` UI harness 不会返回真实 summary；预期结果是明确的 no-LLM 错误。
- 后端 summary 链路使用 mock Sampling 验证，不代表真实模型效果已经验证。
- legacy storage 只保证当前 harness 生命周期内的状态；重启外层 dashboard 后不承诺保留。
- `ui.host_api.llm.complete` compatibility ACL 与 CLI 0.1.37 的已知 runtime 行为绑定，runtime 修复后应重新评估。
- `Working…` loading 过渡太短，未被可靠观察；这仅是附加观察，不作为 `question.md` 的独立未验收项。
- 在真实 RC workflow 和三个 Release assets 完成验证之前，不应声称三平台发布已经成功。
- 本项目没有执行 Anna App 上线，不使用 `anna-app apps push`，也不声明稳定版 `v0.1.0` 已发布。
