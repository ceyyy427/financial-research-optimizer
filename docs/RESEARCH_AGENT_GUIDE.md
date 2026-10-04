# Finathink Research Agent Guide

## Default execution

Finathink 的研究代理默认运行在离线、纸面研究模式。Codex 可以通过显式 handoff envelope 提供研究计划，但本地运行时不会隐式调用当前会话，也不会读取 API key、endpoint 或本机路径。

完整流程是：数据检查 → 多角色研究摘要 → 证据审查 → 因子/量化验证 → 确定性风险门禁 → paper-only decision card → HTML 报告 → as-of 学习记录。

## User-provided providers

用户可以自行提供兼容的 provider adapter。provider 选择的优先级为 defaults → local config → environment → CLI/UI → per-run override。密钥只由外部 adapter 管理，不进入 `ProviderSelection`、prompt、报告、checkpoint 或日志。provider 未配置、能力不足、响应 schema 错误和超时都会产生明确的 typed failure，不会静默换模型。

## Paper-only boundary

研究结果不是投资建议，也不是实时信号。系统不连接券商、不下单、不管理真实资金、不读取高频实时行情。`DecisionCard` 只表达纸面研究配置，必须保留 approval requirement、evidence refs 和 limitations。

## Report bundle

每个 run 生成 `reports/<run_id>/`，其中 `complete_report.html` 是阅读层，`manifest.json`、Artifact、DatasetSnapshot 和 `activity.jsonl` 是可审计事实。报告包含五类分析师、evidence、research、quant、risk 和 paper decision 区块；HTML 由受控 renderer 转义模型和新闻文本。

## Failure classes

`NO_DATA_AVAILABLE`、`DATA_UNAVAILABLE`、`DATA_INVALID`、`PROVIDER_NOT_CONFIGURED`、`VALIDATION_FAILED` 和 `TOOL_REJECTED` 必须分开处理。核心数据、量化或风险失败时，流程不能进入 `PAPER_DECISION_READY`。

