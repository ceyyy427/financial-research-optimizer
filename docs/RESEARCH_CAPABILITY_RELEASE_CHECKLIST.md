# Finathink 研究能力扩展发布清单

更新时间：2026-10-07

这份清单是 Task 9 的离线发布门禁。它描述本地代码和 fixture 的证据，
不把 mock 运行误称为真实数据商、模型服务或交易系统验证。

## 端到端验收

- [x] 用户数据连接配置只保存 credential reference；mock JSON transport 可注入。
- [x] 显式字段映射生成统一 `DataBatch`，记录质量问题、fingerprint 和 `pit_available`。
- [x] 五类角色（fundamentals、technical、sentiment、news、learning）并行运行，输出按角色稳定排序。
- [x] `ResearchManager` 只生成带 evidence refs 的研究计划，不写入事实。
- [x] 因子提案来自固定 DSL 模板；未知 family、未来字段、代码、URL 和路径被拒绝。
- [x] 确定性量化结果包含 OOS 标记；风险失败阻断 DecisionCard。
- [x] DecisionCard 明确 `paper-only`、需要审批、无下单语义。
- [x] 报告包含 `1_analysts/`、`2_evidence/`、`3_research/`、`4_quant/`、`5_risk/`、`6_paper_decision/`、`complete_report.html`、`manifest.json` 和 `activity.jsonl`。
- [x] LearningStore 以 as-of 约束追加记录；ResearchRunStore 校验 identity、workflow、dataset、角色集和 provider capability digest。
- [x] 相同 fixture 输入的 data fingerprint 和非时间性报告文件 digest 稳定。
- [x] 核心失败时 `decision is None` 且 `decision_eligible is False`。
- [x] Artifact、HTML、activity 和 checkpoint 不含 API Key、endpoint、绝对路径、完整 prompt 或 raw provider object。

## 门禁命令

在 capability-expansion worktree 中运行：

```bash
python3 -m pytest -q
python3 -m compileall -q src tests
python3 -m ruff check src tests
python3 scripts/validate_governance.py
python3 -m pip check
cd frontend && npm test
```

另行检查 HTML、SVG、XML 是否可解析，并对 `reports/`、`activity.jsonl`、
`manifest.json`、checkpoint 和前端构建产物运行 secret/path/raw-object 扫描。
Ruff、依赖、前端运行时或 XML 工具不可用时必须写明 `UNVERIFIED`，不能以
pytest 结果替代这些门禁。

## 能力边界

| 分类 | 当前结论 | 证据和限制 |
| --- | --- | --- |
| 已实现 | OFFLINE PASS | 用户数据合同、字段映射、mock connector、分析师池、研究经理、受控因子目录、确定性回测/OOS/风险门禁、paper-only DecisionCard、报告、as-of 学习、checkpoint 已有针对性和回归测试。 |
| 隔离验证 | PASS / DEFERRED | `EngineRegistry` 只接受 Finathink-owned normalized dataset；可选引擎必须通过版本、许可证、隔离、fixture、raw-object boundary、回退和受信 sandbox 门禁。未满足时使用内部确定性引擎。 |
| 未连接 | EXPLICIT | 未连接任何指定数据商、用户真实 API、模型 SDK、QMT、券商、账户、订单、撤单或实时行情服务。 |
| 未验证 | EXPLICIT | 真实凭证可用性、第三方 schema/额度、DNS/网络生产行为、浏览器 E2E、生产部署、外部 sandbox 和 optional-license admission 未由离线 fixture 证明。 |
| 禁止 | PERMANENT | 任何 secret/raw response/endpoint/path/prompt 进入公开 Artifact；任意代码、Shell、SQL、动态 URL；broker/order/live trading；投资建议。 |

## 运行证据

主验收测试：`tests/research/test_capability_vertical_slice.py` 和
`tests/research/test_autonomous_runtime_vertical_slice.py`。
测试使用 `example.test` 的注入 transport 和固定价格记录；它不发起网络
请求。完整测试数量、Ruff、依赖、前端和结构化文档检查的实际结果以
Task 9 report 为准。

## Task 9 全链路组合

- [x] 连接配置重启后可恢复，显式 mock transport 取得标准化数据批次。
- [x] 五类分析师并行运行，ResearchManager 生成证据引用和研究计划。
- [x] 因子 pipeline 完成受控提案、OOS 状态、指标和研究指纹。
- [x] 确定性量化、风险、组合和 paper ledger 可以独立重放。
- [x] SettlementEvent 和 LearningManager 生成 as-of 更新提案。
- [x] HTML bundle、manifest、activity 和 checkpoint 可验证。
- [x] provider mock、Codex handoff、离线 fallback 和队列 retry/cancel/recovery 可重复验收。
- [x] 数据、provider、因子、quant、risk、portfolio 和 worker 失败均保持 `decision is None` 或纸面状态。
