# Finathink 因子—策略—仓位教学工作台设计交接稿

**日期：** 2026-10-05  
**状态：** 设计已获用户确认，交给 Codex 进入实现规划  
**范围：** 因子优化、策略构造、仓位控制、风险状态、执行/滑点、故障降级、深度教学、联动可视化  
**产品边界：** 研究、学习、回测、OOS、纸面模拟和导出；不连接真实资金、券商或自动交易

## 1. 产品核心命题

Finathink 不是“让大模型替用户生成一个因子”的工具，而是把一个人的研究问题变成一条可理解、可验证、可复盘的链：

```text
人的问题
  → 金融概念
  → 数学定义与推导
  → 受控算法结构
  → 安全代码映射
  → 因子与策略实验
  → 仓位/风险/执行约束
  → 回测、OOS、压力情景
  → 结果归因
  → 学习卡与下一步调整
```

每一个可调参数都必须回答：

1. 它在金融上代表什么；
2. 它在数学上如何定义、如何推导；
3. 哪段受控代码实现它；
4. 它如何改变标的选择、仓位、换手、成本和风险；
5. 当前结果为什么变化；
6. 哪些证据支持这个结论，哪些仍未知；
7. 下一步可以怎样调整或证伪。

系统不输出荐股、买卖指令或未来收益承诺。历史结果始终标记为描述性研究证据。

## 2. 现有基础与明确缺口

### 已有能力

- `FactorDefinition`、P6.6 `FeatureDefinition/FeatureVersion/FeatureGraph`：因子与特征的版本化骨架；
- `StrategySpec`、`StrategyIR`、review gate：策略意义和执行结构必须先审阅；
- P5/P5.5 回测：下一周期执行、费用、线性滑点、目标权重、单/多标的实验；
- `ParameterSweepSpecification`、`SweepResult`：参数网格、OOS 字段、稳健/不稳定区域、多个检验警告；
- `ResearchValidity`：时间点、滑点、换手、流动性、容量、杠杆等维度的显式状态；
- `StrategyLearningTrace`、`EducationalCode`、`StrategyLearningBundle`：代码、数学、金融、假设和局限的学习追踪；
- P8.2 research workspace：规范化图表 payload、选中点检查器、参数敏感性可视化。

### 需要补齐的能力

- 因子从“可计算定义”升级为可编辑、可解释、可优化的结构图；
- 因子信号与仓位政策解耦；
- 目标权重经过风险覆盖、约束投影和执行检查后才形成最终目标；
- 回撤、波动、成本和数据故障从“报告字段”升级为可审计的状态机动作；
- 每次参数变化生成数学—代码—金融—结果归因解释包；
- 图表、坐标、参数滑块、解释面板和实验结果双向联动；
- 多模型只产生结构化提案，不执行代码、不改硬边界、不直接运行实验；
- 结果按策略、因子、仓位、风险、执行和解释版本完整保存。

## 3. 完整用户流程

### Stage 0 — 提出研究问题

用户从问题开始，例如：

> 我想知道较长的动量窗口是否能减少噪声和换手，同时不显著损害 OOS 稳定性。

系统把问题拆成假设、可观测量、所需数据、时间边界和限制，不把问题自动改写成“寻找最高收益参数”。

### Stage 1 — 先学概念

在任何参数编辑前，提供：概念、直觉、前置知识、公式、符号、单位、简单手算例子、常见误区和反例。

### Stage 2 — 选择/设计因子

用户从已注册因子中选择，或在受控结构编辑器中组合允许的 primitive：

```text
input → return → rolling → lag → normalize/rank
      → winsorize/neutralize → filter → combine
```

不能输入任意 Python、Shell、网络调用或 broker 操作。

### Stage 3 — 设置仓位与风险政策

因子只输出分数/信号；用户单独设置 `PositionPolicy`、`RiskStatePolicy`、`ExecutionPolicy` 和 `FaultPolicy`。

### Stage 4 — 模型提案

模型读取当前结构、历史诊断、限制和教学上下文，提出：结构变化、参数范围、风险曲线、压力情景和解释。模型输出结构化 diff，用户确认后才进入实验。

### Stage 5 — 冻结实验

系统固定数据指纹、训练/验证/OOS 边界、成本模型、风险硬边界、代码提交和依赖版本，执行基线与变体的确定性对照。

### Stage 6 — 联动可视化

用户拖动参数线、时间坐标或风险阈值，看到信号、选标的、原始仓位、风险缩放、最终仓位、交易、滑点和回撤的同步变化。浏览器只呈现服务端/本地引擎计算好的结果，不自行重算金融指标。

### Stage 7 — 结果解释与复盘

系统生成解释包，按信号、选择、仓位、风险、执行、成本和故障逐层归因，并标出稳健区域、混杂变化、不确定性和限制。

### Stage 8 — OOS、压力和纸面模拟

最终 OOS 只读取一次；压力滑点、数据缺失、价格过期、部分成交和风险触发都要单独显示。通过后才生成新的版本和学习卡，纸面模拟仍无 broker 连接。

## 4. 算法教学标准

每个算法组件都必须有九个区块：

1. **概念**：它是什么；
2. **直觉**：不用公式如何理解；
3. **数学定义**：完整公式、符号、单位；
4. **推导**：每一步为什么成立、使用了什么假设；
5. **代码映射**：参数、IR 节点、函数和输出如何对应；
6. **金融含义**：改变了什么暴露、风险和交易行为；
7. **参数实验**：调大/调小可能改变什么；
8. **结果归因**：本次结果由哪些中间量变化造成；
9. **假设与反例**：何时失效、什么证据会推翻它。

每次参数调整必须生成 `ParameterChangeExplanation`，至少包含：

```text
strategy/parameter identity
before/after
user intent and model proposal
old/new formula and derivation
code/IR trace
finance interpretation
expected effects
paired baseline/variant metrics
signal/selection/sizing/risk/cost attribution
OOS/stress/stability status
assumptions/limitations
next experiment suggestion
```

如果同时改变多个参数，必须标记 `ATTRIBUTION_CONFUNDED`，不能假装得到单参数因果解释。

教学交互采用 Predict → Reveal → Explain：运行前让用户预测方向，运行后显示真实结果，再解释数学、代码和金融原因。

## 5. 仓位政策设计

新增概念性契约 `PositionPolicySpec`，不把仓位逻辑写死在因子或策略模板中。

### 基础映射

第一版支持：

- equal weight；
- rank weight；
- inverse volatility；
- risk budget。

### 风险缩放

```text
risk_scale = min(1, target_volatility / realized_portfolio_volatility)
candidate_weight = base_weight × risk_scale
```

### 约束投影

最终权重必须同时满足：

- 单标的上限；
- 组合总敞口上限；
- 现金缓冲；
- 单次最大调仓量；
- 换手预算；
- 流动性参与率；
- 费用/滑点压力约束。

第一版为长仓、总敞口不超过 1；杠杆作为显式字段和校验保留，超过 1 倍的保证金/融资执行语义另行验证。

## 6. 风险状态机

新增 `RiskStatePolicy`，最小状态集：

```text
NORMAL → CAUTION → DEFENSIVE → FREEZE/FLATTEN → RECOVERY
```

每一状态必须定义：进入条件、退出条件、最短持续时间、滞回、允许动作、触发原因和版本指纹。

触发来源包括：组合波动率、回撤预算、单日损失、连续损失、集中度、换手、成本占比、数据新鲜度和滑点偏离。

动作只允许注册值：`SKIP`、`REDUCE`、`FREEZE`、`FLATTEN`、`FALLBACK`。

回撤阈值先由用户定义最大风险预算 `D`，系统按预算消耗校准状态，而不是由模型自由寻找“最优数字”。

## 7. 执行与故障政策

新增 `ExecutionPolicy`：费用、基准滑点、随波动率变化的滑点、压力滑点、执行延迟、再平衡带宽、最小交易量和流动性参与率。

新增 `FaultPolicy`：

| 故障 | 默认动作 | 允许的替代动作 |
| --- | --- | --- |
| 数据过期/缺失 | `SKIP` | `FALLBACK` |
| 因子计算失败 | `SKIP` | `FREEZE` |
| 实际滑点超过压力上限 | `REDUCE` | `FREEZE` |
| 现金不足/敞口超限 | `REDUCE` | `BLOCK`/拒绝执行 |
| 计算超时 | 失败并保留记录 | 有界重试 |
| 风险预算超限 | `FREEZE` | 用户预先确认的 `FLATTEN` |

故障动作必须可审计、可回滚，不能由模型临时新增。

## 8. 可视化工作台

### 页面结构

```text
┌ 因子与结构 ┐ ┌ 参数/模型提案 ┐ ┌ 数学·代码·金融解释 ┐
├ 信号时间线 ────────────────────────────────────────────┤
│ 价格/因子/排名/入选标的/信号标记/拖动时间坐标           │
├ 仓位与风险 ────────────────────────────────────────────┤
│ 原始权重/风险缩放/最终权重/敞口/现金/回撤/状态区间       │
├ 执行与结果 ────────────────────────────────────────────┤
│ 交易点/换手/费用/滑点/被阻止交易/基线-变体差异          │
├ 解释与学习 ────────────────────────────────────────────┤
│ 推导/代码 trace/金融含义/结果归因/局限/下一步实验        │
└────────────────────────────────────────────────────────┘
```

### 交互规则

- 拖动参数线：生成未提交 preview，不改变已保存版本；
- 点击时间点：同步选中价格、因子、信号、权重、风险状态和交易；
- 点击权重点：显示原始权重、限仓前后、现金/再分配去向；
- 点击风险状态：显示进入条件、触发指标、允许动作和恢复路径；
- 点击任一结果差异：跳转到对应数学、代码和金融解释；
- 所有图表事实必须有表格/键盘替代视图；
- 浏览器不自行计算价格、因子、仓位、风险或回测指标。

### 可视化数据层

扩展现有规范化 research payload，增加：

```text
factor_observations
signals
raw_weights
risk_scales
final_weights
exposure
cash
risk_states
trades
costs/slippage
fault_events
explanation_refs
baseline_variant_refs
```

每个点都绑定 dataset/strategy/policy fingerprint 和 available_at 语义。

## 9. AI 协作协议

新增模型提供商适配层，但所有提供商归一化到本地 `PolicyProposal`：

```text
proposal_id
provider/model metadata
input context fingerprint
target component
allowed parameter diff
reasoning summary
candidate range
required experiments
warnings/limitations
```

模型禁止：任意代码、任意工具、网络/文件/数据库/券商操作、修改硬边界、隐藏失败实验、删除不利结果、将历史结果写成未来承诺。

API key 只从用户本地运行环境读取，不写入策略、实验、日志或导出包。模型调用失败时必须回退到本地确定性工作流。

## 10. 实验与证据标准

每次研究都要保存：

- dataset/available_at/as-of 指纹；
- factor/feature/strategy/policy 版本；
- 训练、验证、OOS 边界；
- 参数搜索空间和实验数量；
- 费用、滑点、执行时序、换手和现金规则；
- 全部实验，包括失败/待处理单元；
- 稳健区域、不稳定区域和多个检验警告；
- 基线/变体对照；
- 压力情景；
- 结果归因和解释包；
- 代码提交、依赖版本、局限和安全扫描。

选择规则禁止“只选最高样本内 Sharpe”。最终应采用邻近参数也相对稳定的区域，或明确报告没有稳定区域。

## 11. 建议的实现分期

### Phase A — 合同和确定性引擎

1. 增加 `PositionPolicySpec`、`RiskStatePolicy`、`ExecutionPolicy`、`FaultPolicy`；
2. 将因子输出与最终目标权重解耦；
3. 实现基础映射、风险缩放、约束投影和状态机；
4. 扩展回测结果、validity 和 provenance；
5. 为每个触发器、降级动作和版本写测试。

### Phase B — 解释包和教学链

1. 扩展 `StrategyLearningTrace` 为完整算法 trace；
2. 实现 `ParameterChangeExplanation`；
3. 添加单参数 paired replay 和结果归因；
4. 将公式、推导、代码、金融解释、限制和练习绑定到具体版本；
5. 生成可导出的学习包。

### Phase C — 可视化工作台

1. 扩展 payload 和图表层；
2. 实现参数 preview、时间线联动、权重/风险/执行叠加；
3. 实现基线/变体对照和解释跳转；
4. 提供可访问表格和键盘交互；
5. 验证浏览器只渲染已计算结果。

### Phase D — 模型提案层

1. 定义 provider-neutral `PolicyProposal`；
2. 接入多个模型 API 的适配边界；
3. 做输入上下文脱敏、提案校验和 hard-boundary 检查；
4. 用户确认后才创建冻结实验；
5. 保存模型和提案 provenance，失败时回退本地流程。

### Phase E — 扩展研究现实度

在前四期稳定后，单独评估：容量、市场冲击、多空、超过 1 倍杠杆、保证金、融资成本和真实数据源。任何一项都不能绕过现有 OOS、validity 和 paper-only 边界。

## 12. 验收标准

### 产品体验

- 用户能从一个问题进入因子、仓位、风险、执行和复盘流程；
- 用户拖动一个参数后能同时看到图表、数学、代码、金融和结果解释；
- 用户能构造自己的交易链条，但每个节点都有明确假设和限制；
- 用户能比较基线与变体，并知道哪些变化无法单独归因；
- 用户能保存、回滚和重新打开一个完整版本。

### 研究完整性

- 因子、策略、仓位和风险政策均版本化、指纹化；
- 无未来信息，OOS 边界冻结且不可用于继续调参；
- 费用、滑点、换手、现金、敞口和故障动作进入结果；
- 所有失败实验保留；不输出“最佳策略”标签；
- 限制、流动性、容量和未建模现实明确显示。

### 教学完整性

- 每个算法组件具备九区块解释；
- 公式能追溯到代码和 IR 节点；
- 结果能追溯到信号、选择、仓位、风险、执行和成本中间量；
- 有练习、预测、揭示、解释和下一步问题；
- 用户能说明“我改了什么、为什么结果变了、证据支持到哪里”。

### 安全完整性

- 模型输出只能形成结构化提案；
- 不执行模型生成代码，不暴露密钥，不连接 broker；
- 故障动作来自固定 allow-list；
- 本地无模型能力时仍可完成确定性研究流程；
- 所有新增接口通过 payload、AST、secret、governance 和回归检查。

## 13. 给 Codex 的执行指令摘要

请以本设计稿为唯一产品方向，先完成合同和确定性引擎，再完成解释包和可视化，最后接入模型提案层。实现时遵守：

1. 不把因子、仓位、风险和执行逻辑混在一个函数里；
2. 不用模型输出直接执行任何代码或交易动作；
3. 不将收益最高的实验称为最佳策略；
4. 不牺牲现有 StrategySpec/StrategyIR、P5/P5.5、ResearchValidity 和 paper-only 边界；
5. 每个新增字段都有 `to_dict()`、指纹和失败状态；
6. 先写失败测试和契约测试，再实现；
7. 每个阶段完成后运行针对性测试、全量回归、Ruff、治理、密钥和打包检查；
8. 最终交付代码、测试、文档、可视化 payload、示例解释包和真实验证报告，明确区分完成、受限和未验证能力。

## 14. Alternate Research Loop：受约束的 AI 自主研究循环

本项目可以吸收你描述的 alternate research 思路，但必须把“自主”定义为**在研究章程内自主迭代**，而不是无限搜索或自动交易。公开的人机协同量化研究也强调迭代式 human-in-the-loop；本项目将其进一步收敛到可学习、可审计、paper-only 的循环。

### 14.1 人先固定 Research Charter

研究开始前，用户必须确认一份不可由模型改写的 `ResearchCharter`：

```text
research_question
hypothesis_scope
dataset_reference and point-in-time rule
data_split: train / validation / test
evaluation_metrics and decision rule
transaction_costs / slippage / execution timing
position, risk and fault hard constraints
allowed primitives and data sources
iteration_budget / compute_budget / wall_clock_budget
maximum experiments and artifact size
paper-only boundary
```

章程一旦冻结，模型只能在 train 和 validation 上研究。test 期的范围、指标和数据指纹对研究代理不可读，直到用户明确执行“freeze and evaluate test”。

### 14.2 研究循环状态机

```text
CHARTER_FROZEN
      ↓
HYPOTHESIS_PROPOSED
      ↓
FACTOR/STRATEGY_CANDIDATE
      ↓
TRAIN_EVALUATION
      ↓
VALIDATION_EVALUATION
      ↓
KEEP / REJECT / REVISE
      ├─ KEEP → CANDIDATE_POOL
      └─ REJECT → ARCHIVED_ATTEMPT
                         ↓
                 下一轮有界研究

CANDIDATE_POOL
      ↓ 用户确认
STRATEGY_FROZEN
      ↓
TEST_EVALUATION
      ↓
RESEARCH_REVIEW
```

每一轮都必须保存输入、假设、提案、参数、代码/IR 指纹、运行状态、指标、解释、失败原因和下一步。无效尝试只能标记 `REJECTED` 或 `SUPERSEDED`，不能从历史中删除。

### 14.3 AI 研究代理的允许行为

AI 可以：

- 从已注册数据和知识层提出金融/数学假设；
- 在允许的 primitive 中构造或修改因子；
- 提议参数范围、权重映射、风险覆盖和压力情景；
- 调用 allow-listed 的确定性研究工具；
- 读取 train/validation 的结果和解释；
- 比较相邻参数、失败原因和稳健区域；
- 给用户讲解每次修改的概念、公式、代码和金融含义；
- 形成下一轮研究计划。

AI 不可以：

- 读取或调参 test/OOS 期；
- 修改 Research Charter 的硬约束、成本、执行规则或预算；
- 删除失败实验或只返回一个最优结果；
- 执行任意 Python/Shell/网络/数据库/broker 操作；
- 将未经用户确认的候选策略固化或连接真实资金；
- 用模型文本代替确定性回测、风险计算或来源证据。

### 14.4 保留、回退和晋级规则

研究代理不以“单次最高收益”为保留标准。每个候选都要经过：

```text
合法性检查
→ 训练表现
→ 验证表现
→ 成本后结果
→ 回撤/CVaR/换手
→ 相邻参数稳定性
→ 压力滑点
→ 研究预算检查
```

只有同时满足章程中的决策规则和风险约束，才进入 `CANDIDATE_POOL`。否则保留完整尝试并回退到最近的已确认版本。晋级理由必须是结构化的，不允许只有“模型认为更好”。

### 14.5 冻结和测试期

冻结动作生成 `StrategyFreezeRecord`：

```text
strategy/factor/position/risk/execution versions
dataset and split fingerprints
charter fingerprint
selected candidate and selection rationale
code commit and dependency versions
model/provider metadata
freeze timestamp
```

冻结后：

1. test 数据才对评估器开放；
2. 任何失败都不能回写训练/验证参数；
3. 若需要修改，必须新建策略版本和新的 Research Charter；
4. 测试结果与训练/验证结果分栏显示；
5. 报告明确写出“历史测试证据，不是未来保证”。

## 15. 可替换的轻量研究架构

研究流程应把数据、目标、约束和执行规则做成可替换输入，而不是把所有逻辑写死在一个策略函数中：

```text
DatasetAdapter
ObjectiveSpec
ConstraintSpec
ExecutionSpec
Factor/Strategy DSL
EvaluationSpec
ResearchCharter
```

核心引擎只消费 Finathink-native 的 JSON-safe contracts。换数据集、目标指标或约束时，必须生成新指纹，不能覆盖旧研究。

### 15.1 仓库连接/API Key 设计

用户可以在工作台中连接一个研究仓库，但接入分层：

**第一阶段：只读导入**

- 用户提供仓库 URL、分支/提交和 API Key；
- 连接器读取 README、锁定依赖、策略说明、测试和允许目录；
- API Key 存入本地安全存储/环境，不进入日志、artifact、模型 prompt 或导出包；
- 记录仓库 URL、commit、license、依赖和读取范围；
- 将可识别的因子/策略映射为 `FactorDefinition`、`FeatureDefinition` 或适配器，不执行未知代码。

**第二阶段：隔离研究适配器**

- 仅在用户明确确认后，在受限、无密钥、无外网的隔离环境运行仓库测试/适配器；
- 只允许产生规范化数据、因子值、权重、指标和日志；
- 任意源代码生成、网络调用、文件删除或 broker 操作都在边界外；
- 所有输出仍需经过 Finathink 的时序、成本、validity、解释和 OOS 检查。

**第三阶段：可选写回**

- 不属于第一版；
- 若以后允许，必须写入新分支/新提交，不能覆盖用户仓库；
- 写回前展示完整 diff、测试结果、风险和教学解释，并要求用户再次确认。

### 15.2 AI 工具对话接口

AI 工具接收到的不是一堆无结构文本，而是带上下文指纹的研究请求：

```text
ResearchCharter
current Factor/Strategy/Policy versions
selected chart point or experiment
allowed tools
train/validation evidence
learning level and requested explanation depth
```

AI 的回答必须引用具体的实验 artifact、解释包和代码 trace；没有对应证据时必须说“当前数据无法支持”。

## 16. 产品价值的最终表达

Finathink 的产物不是一条收益曲线，而是一套可以重新运行的研究资产：

```text
问题与研究章程
+ 数据与时间点规则
+ 因子图与数学推导
+ 策略/仓位/风险/执行版本
+ AI 提出的假设和候选
+ 全部成功与失败实验
+ 训练/验证/OOS/测试结果
+ 图表与中间变量
+ 代码 trace 与金融解释
+ 学习卡、误区和下一步问题
+ 可回滚的版本和完整 provenance
```

它解决的不是“用户不会让 AI 生成因子”，而是：

```text
用户可以做，但不知道为什么；
模型可以跑，但不知道是否可信；
结果有收益，但不知道成本、风险和边界；
研究有尝试，但没有可重复、可学习、可审计的历史。
```

项目最终要让用户能够用自己的数据提出问题、理解算法、观察可视化过程、询问 AI、审阅候选、运行受约束研究、冻结策略、读取测试结果，并清楚地回答：

> 我研究了什么？我为什么这样设计？算法和代码如何实现？结果为什么这样？哪些证据支持它？哪些地方还不能相信？下一步如何继续研究？

