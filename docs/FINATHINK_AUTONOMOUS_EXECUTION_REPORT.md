# Finathink Autonomous Delivery Execution Report

**日期：** 2026-10-05  
**执行分支：** `codex/factor-strategy-workbench`  
**目标：** 将当前对话中确认的 Finathink 方向与 GitHub 参考项目转化为可测试、可审计、可提交到 GitHub 的本地研究产品。

## 一、已确认的产品方向

Finathink 是本地优先的金融研究与学习工作台：用户提供自己的数据，未来可提供自己的模型服务配置；Finathink 负责研究情景、数据审计、因子挖掘、策略构造、仓位/风险/执行模拟、回测、解释、学习记录和离线 HTML 报告。

产品只输出研究证据、纸面决策和可复现工件，明确标记为 `paper-only`；不连接券商、不下真实订单、不托管资金、不把历史结果写成未来承诺。

## 二、当前真实基线

- 因子—策略—仓位工作台已经具备确定性合同、风险状态机、执行/故障政策、解释包、历史研究存储、离线 HTML 报告和只读 UI。
- 多角色研究代理已经具备不可变合同、provider registry、离线驱动、Codex handoff envelope、typed tool gateway、状态机、报告包和 as-of 学习层。
- 已下载并隔离审查 Qlib、RD-Agent、Alphalens Reloaded、PyAnomaly、alpha-mining-system、vectorbt、TradingAgents、FinRobot，位置为：

  `/Users/mac/.codex/references/finathink-github-20261005/`

- 执行起点基线验证：`409 passed, 1 skipped`；因子/Provider/报告增量已经在后续阶段分别通过 focused tests。

## 三、从参考项目吸收的确定性设计

```text
研究情景
  → 研究简报与数据就绪审计
  → 目标/标签与时间点规则
  → 受限因子 DSL 与候选生成
  → 静态检查与确定性计算
  → IC/ICIR/分位数/换手/衰减/成本
  → 样本外与压力验证
  → 因子入库或保留失败记录
  → 策略/仓位/风险/执行模拟
  → 多角色证据审查
  → 决策卡与离线 HTML 报告
  → as-of 学习与下一轮假设
```

Qlib 和 RD-Agent 提供量化研究闭环与因子/模型迭代思想；Alphalens 提供因子验收指标；PyAnomaly 提供资产定价特征和横截面检验；TradingAgents 与 FinRobot 提供角色协作、确定性计算与报告审计结构。所有这些只通过 Finathink-native 合同进入系统。

## 四、必须守住的边界

1. 模型只能提出结构化提案，不能执行任意 Python、Shell、SQL、文件、网络或券商操作。
2. 因子 DSL 只能使用注册字段、注册算子和有界窗口；禁止任意 `eval`。
3. test/OOS 数据在冻结前不可读，失败实验不得删除，不能只显示最高收益结果。
4. API key 只允许作为本地环境/系统密钥引用存在；报告、日志、prompt、checkpoint 和导出包只能记录 provider、模型、引用名和是否已配置，不能记录密钥值。
5. 外部仓库只用于学习和隔离适配实验；不把其数据下载器、交易接口或全套依赖自动接入核心。
6. 任何策略结果都必须标注历史/纸面研究边界、成本、滑点、风险和局限。

## 五、执行阶段与停止标准

### Phase 1 — 因子挖掘核心（已完成）

实现受限 Factor DSL、候选生成、确定性评估、IC/ICIR、分位数收益、换手、衰减、成本和入库判定。

### Phase 2 — 有界研究循环（已完成）

将因子候选接入 ResearchCharter、训练/验证循环、失败历史、显式 freeze/test 和现有多角色研究编排。

### Phase 3 — Provider/API key 安全边界（已完成）

完善 provider 能力状态、用户配置引用、角色到模型映射和 Codex handoff；提供“已配置/未配置/能力不足”的只读状态，不保存或回显密钥。

### Phase 4 — 产品联动与报告（已完成）

让因子候选、评估证据、策略结果、风险状态和解释包进入同一个只读工作台与离线 HTML 报告。

### Phase 5 — 发布审查（执行中）

运行全量 Python/前端测试、静态检查、密钥扫描、编译、离线报告检查、依赖/许可证检查、Git diff 审查和 CI；更新 README、项目状态、变更记录并推送 GitHub。

最终停止条件是：上述五个阶段都有代码、测试、文档和验证证据；未实现的真实 provider、实时数据、broker、自动下单和高频能力必须清楚列为后续范围，而不是伪装成已完成。

## 六、自审结论

本报告与已确认的工作台设计、研究代理计划和 GitHub 参考目录一致，没有把实时交易、用户账户托管或模型任意执行加入范围。因子挖掘、评估/衰减/准入、有界研究循环、Provider 状态、UI 和离线 HTML 联动已经实现；最后只剩全量验证、文档矩阵、Git 状态审查和远程 CI 证据。

已落地的执行提交：

- `22acf72` — execution report and delivery plan
- `87f73cd` — safe factor expression and candidate mining
- `44e090e` — auditable evaluation and admission evidence
- `a636004` — bounded factor research loop
- `f1bd6b9` — secret-free provider readiness status
- `e3ef1cf` — factor evidence in payloads and reports

执行计划见：

`docs/superpowers/plans/2026-10-05-finathink-autonomous-delivery-plan.md`
