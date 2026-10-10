# Finathink 自主研究运行时扩展设计

## 目标

把现有离线研究垂直切片扩展为可恢复、可审计、provider-neutral 的研究运行时：

`用户数据 → 五类分析师 → 研究经理 → 因子研究 → 量化/OOS → 风险经理 → 组合经理 → 纸面交易员 → 学习经理 → HTML 报告`

所有阶段都只产生研究和纸面结果，不连接券商，不读取账户，不下单，不提供投资建议。

## 产品边界

- 用户自行选择数据服务并提供 API 地址和凭证；Finathink 只负责接口合同、字段映射、标准化、质量检查和研究流程。
- 模型只能提出假设、结构化观察和解释；因子数值、回测、OOS、风险、组合约束和 eligibility 由确定性工具判定。
- 模型供应商和数据供应商使用独立的 provider contract、配置命名空间和 credential reference。
- OpenAI-compatible、DeepSeek 等适配器只实现通用 HTTP 合同和 mock 验收，不引入厂商 SDK，不把真实服务可用性当作离线验收结果。
- Codex 编排实现任务 envelope、能力声明、结果回传和失败恢复协议；当前应用不能伪造自己已经自动调用 Codex 服务。离线模式必须可运行。
- 参考项目只作为审查后的资料，保存版本、许可证、哈希和审计结论；不复制其运行时代码，不执行其脚本，不把其依赖加入核心环境。

## 运行时模型

### 阶段图

每次研究运行由 `ResearchRunGraph` 驱动，阶段均有稳定 ID、输入 digest、输出 digest、owner、状态和证据引用：

1. `DATA_READY`
2. `ANALYSTS_READY`
3. `RESEARCH_PLAN_READY`
4. `FACTOR_RESEARCH_READY`
5. `QUANT_VALIDATED`
6. `RISK_REVIEWED`
7. `PORTFOLIO_REVIEWED`
8. `PAPER_DECISION_READY`
9. `LEARNING_RECORDED`
10. `REPORT_PUBLISHED`

任一必需阶段失败即停止决策，产生 typed failure；可恢复阶段只能从匹配的 request、dataset、provider capability、workflow 和 schema digest 恢复。

### 代理角色

- `fundamentals`、`technical`、`sentiment`、`news`、`learning`：并行提出证据索引观察。
- `research_manager`：只综合带 evidence refs 的研究计划和因子假设。
- `risk_manager`：调用确定性风险工具，输出黑天鹅、流动性、集中度、回撤和数据质量约束。
- `portfolio_manager`：根据确定性风险结果和用户配置的 paper-only 约束生成候选权重，禁止发送订单。
- `paper_trader`：只模拟信号、成交、成本和组合轨迹，输出 paper ledger。
- `learning_manager`：在 as-of 结算事件存在时生成可审计的权重/规则更新提案，不直接修改生产因子或风险规则。

所有代理使用统一 `AgentTask`/`AgentOutcome` 合同。代理异常只保留 typed failure、稳定 message digest 和通用消息；原始异常、prompt、密钥、endpoint、raw provider object 不进入状态或 Artifact。

## 模型供应商和 Codex 接口

### ProviderAdapter

统一接口：

```python
invoke(envelope: ModelEnvelope) -> ModelResponse
```

适配器必须声明 provider、model、capabilities、schema version、timeout 和 credential reference。网络请求只能由用户明确配置的适配器发起；模型不能自由指定 URL、工具或文件系统操作。

### CodexBridge

统一接口：

```python
create_handoff(task: AgentTask) -> CodexTaskEnvelope
accept_result(envelope: CodexTaskEnvelope, result: Mapping[str, Any]) -> AgentOutcome
```

envelope 只包含 request/context/prompt 的 digest、角色、能力和 workflow version。结果必须通过 schema、输入 digest、paper-only 和 artifact boundary 校验。无外部回传时返回 `EXTERNAL_HANDOFF_REQUIRED`，不伪造完成。

## 因子研究闭环

自然语言假设只能进入固定 DSL 模板目录：

`Hypothesis → FactorProposal → typed AST → train/validation hidden OOS → freeze → test once-only → IC/ICIR/turnover/decay/rank → human admission proposal`

因子目录必须保存来源、许可证、PIT 语义、版本、输入字段、研究运行 fingerprint 和限制。自动流程只能生成入库候选，不能静默写入生产注册表。

## 风险、组合和纸面交易

- 风险经理只消费 Finathink-owned normalized snapshot 和确定性指标。
- 组合经理只允许 long-only/paper-only 的用户配置约束，所有权重必须经过暴露、集中度、流动性、回撤和压力情景检查。
- 纸面交易员只写 append-only paper ledger，不调用 broker、order、cancel、account 或 live endpoint。
- 风险失败、数据 PIT UNKNOWN/UNAVAILABLE、量化失败或代理缺失时不得产生 `decision_eligible=True`。

## 持久化队列和学习

本地队列使用 SQLite/JSONL 可审计存储，支持 queued/running/retryable/failed/cancelled/completed、指数退避、每运行全局超时、资源配额和幂等 key。worker 不执行任意模型代码，不把密钥放入队列。

学习管理器只读取结算后的纸面事件和已有 Artifact，生成下一轮研究提案。权重、风险规则和因子入库必须经过显式 admission 记录；没有结算证据时输出 `NO_LEARNING_UPDATE`。

## 报告和界面

报告继续使用离线 HTML、manifest、activity、状态墙和 compare workspace。实时阶段流只展示服务端已有状态，不在浏览器重新计算金融指标，不使用“更优策略”或交易建议语言。每个代理、阶段、工具调用摘要、限制、输入/输出 digest 和 checkpoint 状态都可追溯。

## 依赖和参考资料策略

- 核心代码只使用现有 Python 标准库、NumPy/pandas 和既有前端依赖。
- 新依赖必须有固定版本、许可证、离线回退、smoke test 和明确的能力状态。
- 下载的参考项目放在隔离审计目录；先做许可证、危险 API、网络/进程/动态执行和数据边界扫描，再提取可借鉴的接口思想。
- 未经审计的第三方代码、模型输出和压缩包内容均视为不可信数据。

## 验收标准

1. 五类分析师、研究经理、风险经理、组合经理、纸面交易员、学习经理可在离线 fixture 上完成可恢复运行。
2. provider adapter 和 CodexBridge 在 mock 上可验证，未配置外部服务时 typed failure 明确且不伪造成功。
3. 因子闭环可以从假设生成受控 proposal，完成 OOS、排名并生成待入库提案。
4. queue/worker 支持取消、重试、退避、资源限制和幂等恢复。
5. HTML 报告、状态墙、对比界面和学习记录共享同一 run/manifest，全部脱敏。
6. 全量测试、compileall、治理、secret scan、pip check、前端测试、HTML/XML 校验和独立审查通过。

