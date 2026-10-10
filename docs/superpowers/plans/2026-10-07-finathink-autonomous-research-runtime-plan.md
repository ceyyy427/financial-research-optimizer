# Finathink 自主研究运行时扩展实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 provider-neutral、paper-only 研究切片上完成多代理角色、模型/Codex 协议、因子闭环、风险组合、队列 worker、学习和实时报告能力。

**Architecture:** 以 `ResearchRunGraph` 为唯一阶段状态机，以 typed `AgentTask`/`AgentOutcome` 连接代理，以确定性 Python 工具负责所有数值和资格判定。provider、Codex、队列、报告和学习层都通过 digest、checkpoint 和 redaction 边界连接，未配置外部服务时保持离线可运行。

**Tech Stack:** Python 3.11+ 标准库、现有 NumPy/pandas/pytest/ruff、SQLite/JSONL、现有前端 Node 测试工具。核心不新增厂商 SDK、LangGraph、Backtrader 或具体数据商 SDK。

**Spec:** `docs/superpowers/specs/2026-10-07-finathink-autonomous-research-runtime-design.md`

## Global Constraints

- 研究输出永远是 paper-only，不实现券商、账户、真实资金、下单、撤单、持仓托管或投资建议。
- API Key 只能由用户环境变量或系统密钥链以 credential reference 形式提供，不得进入合同、日志、报告、checkpoint、HTML、测试快照或模型上下文。
- 模型只能提出假设、观察和解释；数值、因子、回测、OOS、风险、组合和 eligibility 由确定性工具判定。
- 不复制 TradingAgents、DeepSeek HARNESS、Qlib、RD-Agent、FinRobot 的运行时代码；参考资料只保存审计元数据和经审查的设计知识。
- provider、Codex 和数据接口未配置时必须返回 typed failure 或离线 fixture 结果，不得伪造真实调用成功。
- 任意模型、HTML、配置和参考归档内容均视为不可信数据；禁止任意 Python、Shell、SQL、动态导入、自由 URL、文件系统和网络工具调用。
- 新依赖只有在固定版本、许可证、隔离环境、离线回退和 smoke gate 完整时才可加入。

## Review Focus

- 代理异常、超时、重复角色、部分结果必须稳定排序、脱敏并阻断缺失必需阶段。
- provider/Codex 回传不能越过能力声明、输入 digest、schema、paper-only 和 artifact boundary。
- 因子 proposal 不能包含自由代码、未来字段、隐含 lookahead 或未经审核的来源/许可证。
- 风险/组合/纸面交易不能写 broker/order/cancel/live 入口，风险失败不能生成 paper decision。
- queue 重试、取消、恢复和幂等不能重复写报告、学习记录或纸面 ledger。
- 报告、状态墙、对比界面、checkpoint、学习和队列事件必须共享同一 manifest 且不泄露 secret/endpoint/path/prompt/raw object。

## 执行顺序

第一波可并行：任务 1（角色合同）、任务 2（provider/Codex 合同）、任务 3（因子目录与审核元数据）。任务 4 依赖 1，任务 5 依赖 1–2，任务 6 依赖 1、4，任务 7 依赖 4–6，任务 8 依赖 5、7，任务 9 依赖全部任务。每个任务采用 TDD，完成后由独立 reviewer 审查，再进入下一依赖阶段。

### Task 1: 完整代理角色运行时

**Files:**
- Create: `src/finahinking/research/agent_roles.py`
- Modify: `src/finahinking/research/analyst_runtime.py`, `src/finahinking/research/contracts.py`
- Test: `tests/research/test_agent_roles.py`, `tests/research/test_analyst_runtime.py`

**Interfaces:**
- `AgentRole`、`AgentTask`、`AgentOutcome`：role、task_id、input_digest、capabilities、status、failure_kind、message_digest、evidence_refs。
- `AgentRuntime.run(tasks, driver, context) -> tuple[AgentOutcome, ...]`：支持 analyst、risk_manager、portfolio_manager、paper_trader、learning_manager，输出按 role/task_id 稳定排序。
- `RoleCapabilityPolicy`：声明每类角色允许的输入和工具；风险/组合/纸面角色只能访问确定性 gateway。

- [ ] 写失败测试：七类角色成功、异常、超时、重复角色、必需角色缺失、能力越权和稳定排序。
- [ ] 运行 focused pytest 确认 RED。
- [ ] 实现角色合同和 bounded runtime，保持现有 AnalystPool 兼容。
- [ ] 加测错误脱敏、同输入 digest 稳定、paper-only 能力拒绝。
- [ ] 运行 focused tests、ruff、compileall 并提交 `feat(research): add full agent role runtime`。

### Task 2: ProviderAdapter 与 CodexBridge

**Files:**
- Create: `src/finahinking/research/provider_adapters.py`, `src/finahinking/research/codex_bridge.py`
- Modify: `src/finahinking/research/drivers.py`, `src/finahinking/research/provider_status.py`
- Test: `tests/research/test_provider_adapters.py`, `tests/research/test_codex_bridge.py`

**Interfaces:**
- `ProviderAdapter.invoke(envelope) -> ModelResponse`：注入 transport、timeout、retry policy、credential reference 和 schema version。
- `OpenAICompatibleAdapter`、`DeepSeekCompatibleAdapter`：只实现通用 JSON HTTP contract，默认无真实 endpoint。
- `CodexBridge.create_handoff(task) -> CodexTaskEnvelope`、`accept_result(envelope, result) -> AgentOutcome`。

- [ ] 写 mock transport 的成功、超时、非 JSON、错误状态、schema 错误和 secret-free failure 测试。
- [ ] 写 Codex envelope digest mismatch、能力越权、重复回传、外部 handoff required 测试。
- [ ] 实现 provider-neutral adapters，不引入厂商 SDK，不让模型指定 URL/工具。
- [ ] 运行 provider/research 全量相关测试并提交 `feat(research): add provider and codex bridges`。

### Task 3: 因子研究主流程与审核目录

**Files:**
- Create: `src/finahinking/research/factor_pipeline.py`, `src/finahinking/research/factor_catalog.py`
- Modify: `src/finahinking/research/factor_proposals.py`, `src/finahinking/research/factor_loop.py`
- Test: `tests/research/test_factor_pipeline.py`, `tests/research/test_factor_catalog.py`
- Docs: `docs/FACTOR_CATALOG_AUDIT.md`

**Interfaces:**
- `FactorResearchPipeline.run(hypothesis, dataset, config) -> FactorResearchResult`：proposal、OOS、decay、rank、admission proposal。
- `FactorCatalogEntry`：factor_id、version、source_ids、license_status、pit_semantics、required_fields、research_fingerprint、status。
- `rank_factor_proposals(results) -> tuple[FactorRank, ...]`：只按确定性指标和限制排序，不生成投资建议。

- [ ] 写自然语言到 proposal、OOS hidden/freeze/test-once、IC/ICIR/turnover/decay/rank、来源许可证缺失阻断测试。
- [ ] 运行 RED，再实现 pipeline 和 catalog audit metadata。
- [ ] 加测重复运行 fingerprint、未来字段/lookahead、人工 admission gate。
- [ ] 提交 `feat(factors): connect governed research pipeline`。

### Task 4: 风险、组合和纸面交易代理

**Files:**
- Create: `src/finahinking/research/risk_runtime.py`, `src/finahinking/research/portfolio_runtime.py`, `src/finahinking/research/paper_trader.py`
- Modify: `src/finahinking/research/workflow.py`, `src/finahinking/p6_6/paper.py`
- Test: `tests/research/test_risk_runtime.py`, `tests/research/test_portfolio_runtime.py`, `tests/research/test_paper_trader.py`

**Interfaces:**
- `RiskManager.review(snapshot, factor_result, constraints) -> RiskReviewResult`。
- `PortfolioManager.construct(risk_result, candidates, constraints) -> PaperPortfolioProposal`。
- `PaperTrader.simulate(proposal, snapshot, execution_policy) -> PaperLedger`。

- [ ] 写风险失败、PIT unknown、流动性/集中度/回撤/压力情景阻断测试。
- [ ] 写 long-only paper weights、成本、滑点和 append-only ledger 测试。
- [ ] 写禁止 broker/order/cancel/account/live 调用的 adversarial tests。
- [ ] 接入阶段图，仅在风险和组合通过后产生 paper decision。
- [ ] 提交 `feat(research): add risk portfolio and paper runtimes`。

### Task 5: Durable Queue 与 Worker

**Files:**
- Create: `src/finahinking/research/job_queue.py`, `src/finahinking/research/worker.py`
- Modify: `src/finahinking/research/run_store.py`, `src/finahinking/research/workflow.py`
- Test: `tests/research/test_job_queue.py`, `tests/research/test_worker.py`

**Interfaces:**
- `JobQueue.enqueue(task, idempotency_key) -> JobRecord`、`claim(worker_id) -> JobRecord | None`、`retry(job_id, reason)`、`cancel(job_id)`。
- `ResearchWorker.run_once() -> WorkerResult`：全局 timeout、指数退避、资源配额、checkpoint resume。
- `JobRecord` 不得保存 secret/prompt/raw provider object，只保存 digests 和 references。

- [ ] 写 queued/running/retryable/failed/cancelled/completed、重复幂等、crash recovery、backoff、timeout、cancel 测试。
- [ ] 实现 SQLite/JSONL append-only queue，保持现有 checkpoint 兼容。
- [ ] 加测 worker 不能重复发布报告/学习/ledger。
- [ ] 提交 `feat(research): add durable research job queue`。

### Task 6: 用户数据持久化与研究入口串接

**Files:**
- Modify: `src/finahinking/data/connection_settings.py`, `src/finahinking/local_app.py`, `src/finahinking/research/workflow.py`
- Create: `src/finahinking/data/http_transport.py`
- Test: `tests/data/test_http_transport.py`, `tests/research/test_data_entrypoint.py`
- Docs: `docs/USER_DATA_API_GUIDE.md`

**Interfaces:**
- `PersistentDataConnectionStore`：只持久化 redacted config + credential reference。
- `BoundedHttpTransport`：默认 timeout/response-size/redirect/DNS/connection policy；真实网络只能在用户配置连接中运行。
- `ResearchOrchestrator.run_from_connection(connection_id, request) -> ResearchRunResult`。

- [ ] 写持久化重启恢复、OS keychain reference、默认 HTTP policy、未配置/超时/无数据 typed failure 测试。
- [ ] 连接用户数据入口与长期研究任务，保持 provider-neutral。
- [ ] 禁止真实 transport 自动在保存配置时下载数据；试连必须显式触发。
- [ ] 提交 `feat(data): persist user connections and wire research entrypoint`。

### Task 7: Learning settlement 与受控更新提案

**Files:**
- Create: `src/finahinking/research/settlement.py`, `src/finahinking/research/learning_manager.py`
- Modify: `src/finahinking/research/learning.py`, `src/finahinking/research/run_store.py`
- Test: `tests/research/test_settlement.py`, `tests/research/test_learning_manager.py`

**Interfaces:**
- `SettlementEvent`：paper ledger、as_of、realized outcomes、costs、dataset digest。
- `LearningManager.propose_update(settlement, history) -> LearningUpdateProposal`。
- `admit_update(proposal, admission_record) -> AdmittedUpdate`：没有显式 admission 不能改因子权重、风险规则或 registry。

- [ ] 写无结算 `NO_LEARNING_UPDATE`、as-of、重复结算、缺失 ledger、更新提案 digest 稳定测试。
- [ ] 写因子权重/风险规则只产生 proposal、不自动写生产状态测试。
- [ ] 接入 checkpoint 和报告 learning 阶段。
- [ ] 提交 `feat(research): add settlement-aware learning proposals`。

### Task 8: 实时状态墙、实验对比和报告串接

**Files:**
- Modify: `src/finahinking/research/reports.py`, `src/finahinking/research/ui.py`, `src/finahinking/local_app.py`, `frontend/src/research.js`
- Test: `tests/research/test_live_status.py`, `frontend/test/research.test.mjs`
- Docs: `docs/RESEARCH_RUNTIME_GUIDE.md`

**Interfaces:**
- `research_runtime_view_model(run_id) -> dict`：阶段、角色、工具摘要、重试、checkpoint、learning proposal、manifest digest。
- `compare_experiments(runs) -> dict`：只比较输入/指标/限制，不输出策略优劣或交易建议。
- `GET /api/research/runs/<run_id>/stream`：本地只读阶段快照，不执行浏览器端金融计算。

- [ ] 写阶段流、后台运行、重试、阻断、取消、完成、无 JS fallback 和对比脱敏测试。
- [ ] 实现 UI 只读状态和工具摘要，保持 HTML 报告可离线打开。
- [ ] 提交 `feat(ui): add runtime stream and experiment comparison`。

### Task 9: 端到端发布门禁

**Files:**
- Create: `tests/research/test_autonomous_runtime_vertical_slice.py`
- Modify: `docs/PROJECT_STATE.md`, `README.md`, `docs/RESEARCH_CAPABILITY_RELEASE_CHECKLIST.md`
- Create: `docs/RESEARCH_RUNTIME_RELEASE_CHECKLIST.md`

**Acceptance:**
- 从用户数据连接恢复开始，运行五类分析师、研究经理、因子 pipeline、量化/OOS、风险经理、组合经理、纸面交易员、学习经理、HTML 报告和 checkpoint。
- mock provider/Codex、离线 fallback、队列 retry/cancel/recovery 均可重复验收。
- 任何 provider、数据、因子、量化、风险、组合、worker 或报告阶段失败都不会产生可执行决策。
- 所有公共 Artifact 不含 secret、endpoint、绝对路径、完整 prompt、raw provider object 或 broker/order/live 语义。
- 运行全量 pytest、compileall、ruff（明确既有问题）、治理、secret scan、pip check、前端、HTML/XML，并通过最终独立审查。
- [ ] 先写失败的全链路验收测试。
- [ ] 接入任务 1–8 的最小可用路径并跑完整门禁。
- [ ] 更新中文项目状态、README 和发布清单。
- [ ] 提交 `release(research): complete autonomous research runtime`。

