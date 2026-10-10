# Research runtime status and experiment comparison

Finathink 的研究运行时仍然是本地、只读、paper-only。浏览器只展示服务端已经持久化的阶段状态，不会重新计算收益、风险或任何金融指标。

## 运行时拓扑

API/UI 线程只向 SQLite `JobQueue` 写入任务和读取状态。`ResearchSupervisor`
由独立的非 daemon `spawn` 进程运行，拥有自己的队列连接和静态 stage registry；只有
Supervisor 可以创建 `spawn` worker。worker 只收到版本化、长度受限的 invocation，返回
digest、checkpoint、结果引用和本地预算增量。Supervisor 通过租约围栏将这些状态原子写回
队列，并把指标快照持久化到 `runtime_metrics`，所以进程重启后仍可读取同一份结果。

请求的安全 JSON 快照保存在私有 `request_snapshots` 表中并以请求 digest 绑定；它不保存
API Key、provider 响应或 prompt。默认工作流在 worker 内按 task 引用加载快照，缺失或 digest
不一致时明确失败，不会把失败伪装成成功。

## 阶段状态流

注册研究结果后，应用提供：

`GET /api/research/runs/<run_id>/stream`

该接口返回脱敏的运行时快照，包括：

- `schema_version: 3` 和 `stream: {mode: SERVER_SNAPSHOT, read_only: true, paper_only: true}`；
- `stage_status` / `stages`：数据、分析师、研究计划、量化、风险、组合、纸面决策、学习和报告阶段；
- `role_status` / `roles`：五类分析师及其状态；
- `tool_summaries`：工具名称、状态和摘要指纹；
- `retries`、`checkpoint`、`learning_proposal`；
- `manifest_digest`：报告清单的内容指纹。

快照不包含 prompt、密钥、endpoint、本地路径、原始 provider 对象或原始模型响应。取消、失败、阻断和未配置状态会原样显示，不会被 UI 转换为成功。

研究页同时输出服务器渲染的无 JavaScript 版本。启用 JavaScript 时，`finathink-research.js` 只做 schema 校验和 DOM 渲染；它不调用交易服务，也不在浏览器计算指标。

## 本地 HTTP 旅程验收（2026-10-09）

`tests/p7_5/test_e2e.py` 启动真实 loopback HTTP server，注册离线研究报告，
再通过 HTTP 获取页面与 JSON。`test_http_runtime_journey_has_no_js_navigation_redacted_settings_and_read_only_stream`
验证 `/settings/data-connections`、`/settings/providers`、`/research/browser-e2e-run`
均返回 200；HTMLParser 检查 skip link、可聚焦 main、导航标签、密码输入字段、
无 JS 可读状态和原生报告链接。研究页和完整/运行时报告显示 `READ-ONLY` 与
`PAPER-ONLY`，全部报告链接可通过 HTTP 打开。

同一测试验证 stream v3 的服务端阶段、工具摘要、重试次数和报告链接；
向运行页、完整报告和 stream 发送 POST 均返回 405，随后 GET 快照保持不变。
注入的测试凭证及 artifact 绝对路径未出现在这些页面、报告或 stream 中；
stream 还检查 `api_key`、`prompt`、`endpoint`、`raw_response` 字段不出现。
`test_http_missing_runtime_run_returns_explicit_failure_without_fixture_fallback`
验证缺失 run 的页面、报告和 stream 都返回 404 与明确错误，不回退到其他 run。

本次实际执行：

```text
PYTHONPATH=src /Users/mac/Documents/ChatGPT/Finahinking\ Autonomous\ Builder/.venv/bin/python -m pytest tests/p7_5/test_e2e.py -q
3 passed in 3.25s

cd frontend && npm test
17 passed, 0 failed
```

证据状态为 `OFFLINE_BROWSER_PASS`。Playwright 1.61 驱动本机 Chromium 1243
实际打开 loopback 页面，验证 JavaScript-disabled 页面、密码字段、skip-link 与
Tab traversal、失败 run、报告跳转、stream-fetch 错误提示，以及桌面/390px
移动端无横向溢出。页面/console error 收集结果为空。截图、HTML 和 SHA-256
清单保存在 `.superpowers/sdd/2026-10-08-research-capability-completion-plan/task-16-artifacts/`。
这仍是本地离线证据，不代表外部 provider、生产部署或屏幕阅读器一致性已验证。

## 实验对比

`compare_experiments(runs)` 只返回每个运行的 `inputs`、服务端已有 `metrics` 和 `limitations`。它不判断哪个策略更好，不生成交易建议，也不把限制条件隐藏起来。比较结果可以嵌入离线 HTML 报告或状态墙中。

## 报告边界

报告继续使用可离线打开的 HTML、manifest 和 activity 文件。所有路由是只读的；任何写入、下单、账户访问和 broker 操作都不属于该运行时。

## 兼容模型契约探针

`OpenAICompatibleAdapter` 和 `DeepSeekCompatibleAdapter` 只依赖注入的
`JsonTransport`，发送无 prompt 的摘要字段和标准 chat-completions 字段，
并将响应收敛为 `ProviderContractResult`。401/403、429、5xx、超时、非 JSON
和 schema 错误只产生稳定状态，不保存密钥、endpoint、原始响应或模型 prompt。
429 与 5xx 使用最多 5 次的有界重试；退避由 `RetryPolicy` 控制。

默认测试永远离线。只有同时设置
`FINAHINKING_LIVE_PROVIDER_TEST=1`、provider/model/endpoint 和凭证引用环境变量，
并显式注入 transport，才允许构造验收适配器；代码不会因环境变量存在而自动联网。
