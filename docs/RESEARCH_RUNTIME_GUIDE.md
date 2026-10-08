# Research runtime status and experiment comparison

Finathink 的研究运行时仍然是本地、只读、paper-only。浏览器只展示服务端已经持久化的阶段状态，不会重新计算收益、风险或任何金融指标。

## 阶段状态流

注册研究结果后，应用提供：

`GET /api/research/runs/<run_id>/stream`

该接口返回脱敏的运行时快照，包括：

- `stage_status` / `stages`：数据、分析师、研究计划、量化、风险、组合、纸面决策、学习和报告阶段；
- `role_status` / `roles`：五类分析师及其状态；
- `tool_summaries`：工具名称、状态和摘要指纹；
- `retries`、`checkpoint`、`learning_proposal`；
- `manifest_digest`：报告清单的内容指纹。

快照不包含 prompt、密钥、endpoint、本地路径、原始 provider 对象或原始模型响应。取消、失败、阻断和未配置状态会原样显示，不会被 UI 转换为成功。

研究页同时输出服务器渲染的无 JavaScript 版本。启用 JavaScript 时，`finathink-research.js` 只做 schema 校验和 DOM 渲染；它不调用交易服务，也不在浏览器计算指标。

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
