# Finathink Quant-Harness + TradingAgents 合体设计规范

**状态：待用户审阅，不是实现批准**  
**日期：2026-10-04（Asia/Shanghai）**

## 1. 设计目标

本设计把两个外部参考工程的可复用思想，接入 Finathink 当前的研究型、证据优先、可复现边界：

- `/Users/mac/Downloads/deepseek-harness-quant-master.zip`
- `/Users/mac/Documents/Codex/2026-10-03/codex-plugin-marketplace-add-yuuhann1999-agent/TradingAgents.zip`

目标不是把两个工程拼成一个大型交易程序，而是形成一个“模型协作层 + 确定性研究引擎 + 可追溯报告”的长期架构：

```text
自然语言研究问题
    -> ModelDriver / 多代理协作层
    -> 结构化研究计划与分析报告
    -> Finathink 类型化工具网关
    -> 数据、因子、回测、OOS、风险验证
    -> Artifact / ResearchRun / QuantRun
    -> HTML 报告 + 纸面 DecisionCard
    -> 用户复核与学习记录
```

核心原则：

1. 模型负责提出问题、假设、研究路径和解释，不直接成为事实源。
2. Finathink 现有的 Dataset、PIT/as-of、回测、Artifact、ResearchRun、QuantRun 和安全网关继续作为权威边界。
3. 多代理只负责协作与证据整理；所有可计算结论必须由确定性工具执行。
4. 第一阶段只产生研究结果和纸面决策，不连接券商、真实账户或真实资金。
5. HTML 是主要阅读产物，机器可读 JSON、指纹和 Artifact 是事实载体。

## 2. 参考工程取舍

### 2.1 DeepSeek HARNESS Quant 取用的设计

保留以下思想，但重新实现为 Finathink 契约：

- 数据入口统一化、PIT 和数据质量闸门；
- 因子注册表、因子方向、因子健康、衰减和共线性治理；
- “自然语言提出假设，确定性引擎验证”的九步因子入池流程；
- 数据审计、流动性、财务质量、假信号和风险门控；
- Skill 作为方法论、验收标准和常见陷阱的载体；
- 决策卡和报告按阶段组织，并可追溯到回测与风险证据。

不直接复制：

- `harness/plugins/dsq-quant-bridge/index.js` 的插件和 subprocess 运行方式；
- 任意 `eval()`、Shell、动态热补丁和不受限路径访问；
- `backtrader` 等未经 Finathink 依赖审查的组件；
- 参考工程 README 中尚未被统一测试门禁证明的能力声明；
- 空白或未验证的“牛散” persona 作为事实或决策依据。

### 2.2 TradingAgents 取用的设计

参考项目已存在本地只读审查记录：`docs/p8_2/TRADINGAGENTS_REFERENCE_REVIEW.md`。本设计进一步把下列模式纳入目标架构：

- 基本面、技术、情绪、新闻等分析角色并行运行；
- 所有分析完成后，再启动研究综合和批判讨论；
- 研究经理、交易提案、风险复核和组合研究之间有清晰的阶段边界；
- 每个阶段拥有 `pending / in_progress / completed / error` 等真实状态；
- 工具调用、模型消息、报告内容和统计信息分开保存；
- 通过配置和提供商注册表为不同角色选择不同模型；
- 对无数据、供应商不可用、未配置和研究失败进行不同处理；
- checkpoint 身份包含 ticker、日期、分析师集合、研究深度、配置指纹和图版本；
- 每个运行保存分区报告和一份汇总报告；
- 运行结果、历史记忆和 backtest 使用不同的持久化边界；
- 结构化输出优先，结构化失败时只能降级为“非决策型报告”，不能静默生成决策。

不直接复制：

- `BUY / SELL / HOLD` 作为 Finathink 产品的投资建议语义；
- Trader、Portfolio Manager 或 broker 的真实执行语义；
- TradingAgents 的 LangGraph、Pydantic、外部 vendor 和领域命名直接进入 Finathink 核心；
- 用模型辩论替代因子、回测和风险事实；
- 把模型的随机输出包装成可重复的 Alpha 结论。

## 3. 产品边界、使用者与生命周期

### 3.1 目标使用者

第一阶段面向单用户、本地优先的研究者：

- 用户可以配置自己购买且合规使用的数据源；
- 用户可以为不同分析角色选择不同的模型提供商；
- 用户可以选择研究对象、分析师集合、研究深度和学习范围；
- 用户可以查看逐阶段报告、证据和限制，并将结果用于纸面研究。

### 3.2 不可悄悄扩大的范围

以下事项不属于本设计的默认能力：

- 实盘下单、券商连接、账户余额或持仓的自动读取；
- 模型直接生成并执行 Python、Shell、SQL、浏览器脚本或插件代码；
- 自动将模型输出写入因子注册表、风险规则或历史事实；
- 以模型共识代替数据质量检查、前视检查、OOS 或人工复核；
- 将未经验证的外部行情、新闻、社交文本作为确定事实；
- 把纸面 DecisionCard 呈现为投资建议、收益承诺或交易指令。

## 4. 总体架构

```text
┌───────────────────────────────────────────────────────────────┐
│ 用户 / Codex / ChatGPT / API 客户端                           │
└───────────────────────┬───────────────────────────────────────┘
                        ▼
┌───────────────────────────────────────────────────────────────┐
│ ModelDriver 层                                                 │
│ 角色路由、提供商能力、结构化输出、重试上限、上下文裁剪          │
└───────────────────────┬───────────────────────────────────────┘
                        ▼
┌───────────────────────────────────────────────────────────────┐
│ Research Orchestrator                                           │
│ 状态机、并行阶段、checkpoint、取消、阶段边界、失败传播          │
└───────────────┬───────────────────────────────┬───────────────┘
                ▼                               ▼
┌──────────────────────────┐       ┌────────────────────────────┐
│ Analyst / Research Agents │       │ Learning Analyst / Manager  │
│ fundamentals / technical  │       │ as-of lessons / reflection  │
│ sentiment / news / method │       │ evidence-linked learning    │
└───────────────┬──────────┘       └──────────────┬─────────────┘
                └──────────────────┬──────────────┘
                                   ▼
┌───────────────────────────────────────────────────────────────┐
│ Typed Tool Gateway                                              │
│ data snapshot / factor / backtest / OOS / risk / inspect / report│
└───────────────┬───────────────────────────────────────────────┘
                ▼
┌───────────────────────────────────────────────────────────────┐
│ Finathink 权威引擎                                               │
│ providers → Dataset/PIT → features/factors → quant → risk       │
└───────────────┬───────────────────────────────────────────────┘
                ▼
┌───────────────────────────────────────────────────────────────┐
│ Artifact / ResearchRun / QuantRun / Learning Evidence            │
└───────────────┬───────────────────────────────────────────────┘
                ▼
┌───────────────────────────────────────────────────────────────┐
│ HTML Report Bundle + paper-only DecisionCard + UI status wall     │
└───────────────────────────────────────────────────────────────┘
```

### 4.1 ModelDriver

`ModelDriver` 是模型无关接口。它接收经过裁剪和授权的上下文，返回结构化的研究输出或明确的失败状态。

首期适配器：

- `CodexInteractiveDriver`：由当前 Codex 会话协作提出计划和解释，不能由本地服务隐式调用当前对话；
- `OfflineDriver`：使用固定 fixture 生成确定性测试输出；
- `UserApiDriver`：为以后接入用户自备 API 保留接口；
- `CompatibleApiDriver`：面向用户自行配置的 OpenAI-compatible endpoint。

“ChatGPT、Codex、DeepSeek、Cloud”不自动等于同一个运行时。每个 provider 必须通过能力注册表声明是否支持：

- 结构化输出；
- 工具调用；
- 流式输出；
- reasoning/thinking 参数；
- 最大上下文和输出 token；
- 取消与重试；
- 数据驻留与日志策略。

未注册、未配置或能力不匹配的 provider 必须显示为不可用，不得静默改用另一个模型。

### 4.2 多代理角色

角色是研究工作流中的职责，不是可直接下单的交易员：

| 角色 | 输入 | 输出 | 默认权限 |
|---|---|---|---|
| 基本面研究员 | PIT 财报、指标、来源 | 结构化基本面报告 | 只读数据工具 |
| 技术/市场研究员 | 价格、成交量、技术特征 | 技术状态和限制 | 只读数据工具 |
| 情绪/资金研究员 | 经过时间过滤的情绪/资金数据 | 情绪证据和失效条件 | 只读数据工具 |
| 新闻/宏观研究员 | as-of 新闻、宏观、事件 | 来源绑定的事件摘要 | 只读数据工具 |
| 学习研究员 | as-of 历史结果、失败案例、知识单元 | 可迁移方法和反例 | 只读学习工具 |
| 多空证据评审 | 已完成的分析报告 | 支持、反驳、缺口 | 不可新取数据 |
| 研究经理 | 分析与评审结果 | ResearchPlan / 研究结论 | 不可写事实 |
| 风险复核组 | 研究计划、风险指标 | RiskReview | 不可修改历史结果 |
| 纸面配置经理 | 研究结论和 RiskReview | paper-only AllocationProposal | 不可连接券商 |
| 学习层经理 | 完成后的报告和后验结果 | LearningEvidence | 只追加学习记录 |

每个代理的输出都必须经过 Schema 校验。自然语言正文可以保存，但机器流程只消费结构化字段和 Artifact 引用。

### 4.3 阶段状态机

建议状态：

```text
RECEIVED
→ IDENTIFIED
→ DATA_CHECKED
→ ANALYSTS_RUNNING
→ ANALYSTS_READY
→ EVIDENCE_REVIEW
→ RESEARCH_PLAN_READY
→ QUANT_VALIDATION
→ RISK_REVIEW
→ PAPER_DECISION_READY
→ REPORT_PUBLISHED
→ LEARNING_RECORDED
```

终态包括：`REJECTED`、`NO_DATA_AVAILABLE`、`DATA_UNAVAILABLE`、`PROVIDER_NOT_CONFIGURED`、`VALIDATION_FAILED`、`CANCELLED`、`FAILED`。

阶段转移必须通过显式 path map。分析师可以并行运行，但综合阶段只有在声明的输入全部完成或被显式标记为不可用后才能启动。

### 4.4 工具网关

模型只能调用 Finathink 已注册的工具名称和 JSON 参数：

- `research.inspect_dataset`
- `research.resolve_instrument`
- `research.compute_factor`
- `quant.run_backtest`
- `quant.run_regression`
- `quant.evaluate_performance`
- `quant.analyze_risk`
- `quant.inspect_run`
- `research.render_report`
- `learning.inspect_asof_lessons`
- `learning.record_evidence`

工具网关必须沿用当前 `src/finahinking/quant/services.py` 和 P6 gateway 的安全思路：拒绝可执行内容、任意路径、凭证、动态导入、删除/改写历史和未注册工具。

## 5. 数据、因子、回测和风控边界

### 5.1 数据入口

用户自备数据源通过 provider adapter 接入：

```text
ProviderConfig
    → ProviderRegistry
    → normalized observations
    → DatasetSnapshot
    → schema / missingness / time / PIT validation
```

`ProviderConfig` 记录提供商标识、数据类别、as-of 语义、使用条件和能力声明，但不把 API key 写入报告、Artifact、模型上下文或 Git。

数据状态必须区分：

- `NO_DATA_AVAILABLE`：该标的在该时间点确实没有可用数据；
- `DATA_UNAVAILABLE`：供应商未配置、请求失败或暂时不可用；
- `DATA_INVALID`：数据返回但无法通过 schema、PIT 或质量检查；
- `DATA_PENDING`：正在等待或稍后才能结算的数据。

模型不得对这些状态进行估值、补写或“合理猜测”。

### 5.2 因子层

参考工程声称拥有 123+ 个因子，但这在本设计中只作为待审阅目录，不作为已验证事实。首期只接入少量代表因子。

每个 `FactorDefinition` 至少包含：

- `factor_id`、`version`、`definition`、`formula_or_expression`；
- 输入字段、数据源、PIT/as-of 要求；
- signal family、方向、缺失处理和数值范围；
- 来源、许可证和参考链接；
- validation status、适用时间窗和已知局限；
- 健康状态：`VALID`、`DECAYING`、`REVERSED`、`INSUFFICIENT_DATA`、`RETIRED`。

因子入池沿用“假设 → 计算 → IC/ICIR → 去重 → T+1 → 年度/OOS → 正交/容量 → 归档或证伪”的工作流。模型可以提出因子候选，不能单独将因子标记为有效。

### 5.3 回测和 OOS

回测继续由 Finathink P5/P6.6 负责，至少保留：

- 明确的 T+1 对齐；
- 成本、滑点、频率、基准和窗口记录；
- 数据集、策略、引擎、代码提交和依赖指纹；
- 结果与限制分离；
- in-sample、OOS、paper-only 的明确标签。

TradingAgents 的 LLM backtest 只能作为“模型决策随时间评估”的补充研究，不得替代确定性量化回测，也不能把随机模型输出包装成固定绩效。

### 5.4 风险层

风险层分成两部分：

1. **确定性风险计算**：数据质量、前视、缺失、流动性、波动、回撤、暴露、共线性和因子健康。
2. **模型辅助风险解释**：对确定性结果做摘要、反例、缺口说明和人工复核提示。

模型提出的规则必须成为版本化 `RiskPolicyProposal`，经历：

```text
提出 → Schema 校验 → 离线验证 → 反例/敏感性检查 → 人工批准 → 注册表新版本
```

没有批准的规则只能显示为候选，不能直接改变风险门控。

## 6. 报告与持久化

### 6.1 HTML 报告包

每个完成的运行生成一个报告包：

```text
reports/<run_id>/
├── complete_report.html
├── manifest.json
├── 1_analysts/
│   ├── fundamentals.html
│   ├── technical.html
│   ├── sentiment.html
│   ├── news.html
│   └── learning.html
├── 2_evidence/
├── 3_research/
├── 4_quant/
├── 5_risk/
├── 6_paper_decision/
└── activity.jsonl
```

HTML 是阅读层，必须由受控渲染器生成并转义模型内容；模型不得直接注入脚本、事件处理器或任意 HTML。`manifest.json` 是机器层，记录报告段落、输入 Artifact、状态、限制和指纹。

### 6.2 Finathink 权威记录

报告包只引用而不替换：

- `ResearchRun`：问题、假设、数据、因子、方法和结论；
- `QuantRun`：回测/OOS 结果、参数和运行指纹；
- `Artifact`：大小受限、JSON-safe、可验证的结果载荷；
- P7 学习和历史记录：只保存经过权限和来源检查的投影。

自由文本报告不是新的事实源。若 HTML 与 Artifact 不一致，以 Artifact 和其指纹为准，报告标记为 `STALE` 或 `INVALID`。

### 6.3 记忆与学习层

学习层可以借鉴 TradingAgents 的反思和结算机制，但必须遵守 as-of：

- 运行时只读当时已经存在的历史经验；
- 后验收益和新证据在结算日期之后才能进入学习记录；
- 未结算的历史条目状态为 `PENDING`；
- 学习记录只追加，不重写原始研究结论；
- 学习经验必须链接到原始 Artifact、数据窗口和结算时间。

## 7. 提供商和配置

配置优先级建议为：

```text
安全默认值
→ 本地配置文件
→ 环境变量
→ CLI / UI 显式选择
→ 本次运行的临时覆盖
```

每次运行保存经过脱敏的 `ProviderSelection`：

- provider id；
- model id；
- 角色映射；
- endpoint 的非敏感标识；
- 能力快照；
- temperature/reasoning/max tokens 等已生效参数；
- 配置指纹。

报告不得保存 API key、Authorization header、完整 endpoint secret、个人路径或机器身份信息。

同一次运行中，不允许未声明地切换提供商。重试只能在配置的上限内进行，并把 `RETRYING`、`UNAVAILABLE` 和最终失败区分开。

## 8. 可靠性、错误和恢复

### 8.1 并行和边界

- 无共享写入的分析师阶段可以并行；
- 每个代理有最大工具轮数和超时；
- 研究辩论和风险讨论有最大轮数；
- 单个可选分析师失败时，可以进入 `PARTIAL_ANALYSIS`，但必须在报告中显示；
- 核心数据、量化或风险阶段失败时，不得生成 `PAPER_DECISION_READY`。

### 8.2 checkpoint

checkpoint 指纹至少包含：

- 标的/资产身份和分析日期；
- DatasetSnapshot 指纹；
- 选中的分析师集合；
- 角色—模型映射；
- Skill 版本和工作流图版本；
- 研究深度、最大轮数和配置指纹；
- 输入的 ResearchPlan 指纹。

不兼容的 checkpoint 不得恢复。成功完成后清理临时 checkpoint，但保留不可变的最终 Artifact 和报告。

### 8.3 可恢复状态

UI 和 API 必须显示：

- 当前阶段；
- 已完成/总阶段；
- 每个代理的状态；
- 最后一个工具调用及其结果状态；
- 可恢复的失败原因；
- 是否有部分报告；
- 是否可以安全重试。

不得用“正在分析”掩盖 `NO_DATA_AVAILABLE`、`PROVIDER_NOT_CONFIGURED` 或失败。

## 9. 安全和合规

### 9.1 不可信内容边界

外部新闻、社交文本、模型回复、Skill 文本和 HTML 内容都是数据，不是系统指令。它们不能改变工具权限、文件路径、SQL、Shell 或安全策略。

### 9.2 凭证边界

- 凭证由用户自行配置；
- 凭证只进入 provider client；
- 凭证不进入 prompt、报告、Artifact、日志或 checkpoint；
- 测试使用假凭证并包含 secret scan；
- API key 一旦出现在对话或日志中，视为已暴露并要求用户轮换。

### 9.3 输出边界

所有最终报告和 DecisionCard 都必须显示：

- 研究用途说明；
- 数据窗口和来源；
- 模型与工具参与情况；
- 数据和模型局限；
- 是否为 paper-only；
- 未通过的门禁和缺失证据。

## 10. 实施拆分

本设计批准后再进入实现计划。建议拆成以下可审查阶段：

### Phase A：契约和离线垂直切片

- `ResearchRequest`、`ResearchPlan`、`AgentReport`、`RiskReview`、`DecisionCard`、`ReportManifest`；
- `ModelDriver`、ProviderRegistry 和能力检查；
- OfflineDriver + 现有 fixture；
- 5 个分析角色的并行状态机；
- 生成 HTML + JSON 报告包；
- 不访问真实网络、不接用户凭证、不写新生产数据。

### Phase B：Finathink 工具接入

- 接入现有 dataset/factor/quant/risk gateway；
- 引入因子注册表和健康状态；
- 建立九步因子验证工作流；
- 让 RiskReview 只消费确定性风险结果；
- 把结果链接到 ResearchRun、QuantRun 和 Artifact。

### Phase C：学习层和历史结算

- as-of 历史学习读取；
- 结果结算与反思记录；
- 失败案例、反例和技能版本的证据链接；
- P7 权限范围和个人连续性检查。

### Phase D：用户自备 Provider

- 首先支持已审查的 OpenAI-compatible adapter；
- 再按能力注册表添加 OpenAI、DeepSeek、Anthropic、Google 等 provider；
- ChatGPT/Codex 作为产品侧交互入口时，仍通过 ModelDriver，不把桌面会话当作隐式后端 API；
- 任何真实网络路径都必须有超时、重试、速率、数据驻留和脱敏验证。

### Phase E：研究 UI

- 阶段状态墙；
- 分析师报告卡；
- 证据/工具时间线；
- HTML 报告浏览器；
- 因子健康和风控门禁页；
- 纸面 DecisionCard；
- 失败、缺数据和不可用状态的可访问显示。

真实交易执行不属于以上阶段。

## 11. 验证策略

### 11.1 契约测试

- JSON Schema、标识符、时间、数值和 fingerprint；
- 禁止可执行内容、路径、凭证和动态导入；
- 报告 JSON 与 HTML manifest 一致；
- HTML 转义和脚本注入防护；
- provider 配置脱敏与优先级；
- 未配置 provider、能力不匹配和重试上限。

### 11.2 工作流测试

- 分析师并行后才进入综合；
- 任一阶段的显式失败状态可见；
- 最大工具轮数/辩论轮数生效；
- 不兼容 checkpoint 被拒绝；
- 可选分析失败生成部分报告但不伪造完整性；
- 核心量化或风险失败阻止纸面决策就绪。

### 11.3 金融研究测试

- PIT/as-of 和前视检查；
- T+1、成本、缺失和不可成交条件；
- OOS 窗口、样本数和限制披露；
- 因子方向、衰减、共线性和健康状态；
- 学习记录不能读取未来结算结果。

### 11.4 垂直验收

用固定 fixture 完成：

```text
ResearchRequest
→ Offline 多代理报告
→ ResearchPlan
→ 确定性 QuantRun
→ RiskReview
→ paper-only DecisionCard
→ HTML + JSON + Artifact
```

连续运行两次时，确定性数据、工具结果和 Artifact 指纹必须一致；模型正文可明确标记为非确定性或使用 OfflineDriver 固定输出。

## 12. 依赖、迁移和回滚

### 12.1 依赖原则

- 不把 TradingAgents 或 DeepSeek HARNESS 作为 Finathink 运行时依赖；
- 不直接引入 LangGraph、Backtrader 或 provider SDK，除非单独完成依赖、许可证和适配器审查；
- 首期使用现有 Python/Pandas/NumPy 和 Finathink 自有状态机、Artifact、gateway；
- 任何新增 provider 都通过隔离 adapter 和能力测试进入。

### 12.2 迁移策略

- 所有新表、新 Artifact 类型和新报告格式采用 additive schema version；
- 现有 P4–P8 Artifact 不重写；
- 参考项目中的因子先进入“参考目录”而不是有效因子池；
- 新工作流用 feature flag 启用；
- 旧研究路径继续可用，直到新路径通过完整垂直验收。

### 12.3 回滚策略

- 关闭多代理 feature flag 即回到现有 Finathink 研究流程；
- 删除未发布的 run workspace 不影响已有 Artifact；
- provider adapter 失败时回到 OfflineDriver 或明确不可用，不自动切换到未知模型；
- 报告 renderer 失败时保留 JSON 和原始 Artifact，不覆盖旧报告；
- 任何规则或因子升级通过新版本和新指纹发布，旧版本保持可读取。

## 13. 决策请求

本规范需要用户确认以下三个关键点后，才能进入实现计划：

1. 是否采用“Finathink 为权威引擎，两个外部工程只提供可审查模式”的适配式融合，而不是整体复制？
2. 是否同意第一阶段的“一键执行”只指研究流程、HTML 报告和 paper-only DecisionCard，不连接真实交易？
3. 是否同意把 Codex 视为交互式 ModelDriver，并为未来的用户自备 API 保留独立 provider adapter，而不假定项目可以隐式调用当前 Codex 对话？

确认后，下一步才是编写逐文件的实现计划；实现计划会继续经过单独审阅，不会因为本设计获批就自动开始编码。
