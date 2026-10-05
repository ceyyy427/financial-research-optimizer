# Finathink 研究能力扩展实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有离线研究垂直切片之上，逐步落地可并行、可恢复、可审计的多分析师研究运行时、用户自备模型接口、用户自备数据 API 接口、受控因子提案循环、研究报告和可选量化引擎适配能力。

**Architecture:** Finathink 是用户自带数据的数据处理与研究平台：用户选择数据源并提供 API 配置，平台只负责统一接入、字段映射、清洗、分析和产物保存。新增研究能力只通过类型化接口进入：分析师并行产生结构化观察，研究经理综合证据，确定性引擎完成因子/回测/风险验证，最后写入不可变 Artifact、HTML 报告和 append-only 学习记录。外部模型与可选量化引擎是可替换适配器；数据连接器不绑定具体数据商。

**Tech Stack:** Python 3.11+ 标准库（`concurrent.futures`、`dataclasses`、`json`、`sqlite3`/JSONL）、现有 NumPy/pandas/pytest/ruff；前端只消费服务端生成的脱敏状态，不在浏览器计算金融指标。

**Spec:** `docs/superpowers/specs/2026-10-04-finathink-quant-harness-tradingagents-design.md`、`docs/superpowers/specs/2026-10-05-finathink-factor-strategy-workbench-design.md`、`docs/p8_2/P8_2_RESEARCH_ENGINE_ARCHITECTURE.md`；数据接入范围以 `docs/superpowers/specs/2026-10-06-finathink-user-data-interface-scope.md` 和用户本次说明为准，不沿用旧文档中具体数据商的接通目标。

## 已存在能力与本计划边界

当前 `main` 已有：不可变研究合同、Offline/Codex/User API driver 边界、typed tool gateway、单次离线编排器、因子注册/健康/提案评估、HTML 报告包、as-of 学习存储、provider readiness、只读研究 UI 和离线垂直切片。本计划不重复这些实现，而是把它们推进为可扩展的运行时。

### 2026-10-06 用户补充：数据来源由用户决定

- 用户负责选择数据商、取得数据访问权限、提供自己的 API 地址和 API Key；Finathink 不替用户找数据、购买数据、申请账号或审核每家数据商。
- 本计划只实现供应商无关的数据接入接口与配置体验：连接配置 → 用户数据 API → 字段映射 → 统一数据格式 → 清洗/分析/研究。
- 不以接通 QMT、AkShare、Tushare 或其他指定数据商作为本计划验收前提；不下载行情包、登录用户账号或购买数据。
- 数据格式、缺失值、重复记录、时间戳、响应大小与密钥安全属于接口责任，不是数据来源审查。来源名称是用户提供的元信息，不代表平台已经核验其真实性或授权。
- 未提供可用时间/修订时间的数据不自动视为 PIT 数据；可以接收并展示其缺口，依赖该信息的历史研究必须明确受限，不能凭空补齐。
- 模型 API 和数据 API 使用不同配置命名空间及凭证引用，不自动共用密钥。

## Global Constraints

- 研究输出永远是 `paper-only`；不实现券商连接、账户读取、真实资金、下单、撤单、持仓托管或投资建议。
- 模型只提出假设、结构化观察和解释；所有数值、因子、回测、OOS、风险和 eligibility 由 Finathink 确定性工具判定。
- 不复制 TradingAgents、DeepSeek HARNESS、Qlib、RD-Agent、FinRobot 的运行时代码；只吸收经审查的边界、阶段、报告和恢复模式。
- 不引入 LangGraph、Backtrader、OpenAI/DeepSeek SDK 或具体数据商 SDK 作为核心依赖；通用数据接口不依赖指定供应商。新增软件依赖仍须做版本、许可证、隔离环境和离线回退检查，这不是对用户数据来源的审查。
- API Key 只能由用户环境变量或系统密钥链以 credential reference 形式提供；不得写入合同、日志、报告、checkpoint、HTML、测试快照或模型上下文。
- Provider 未配置、无数据、数据无效、模型超时、Schema 错误、工具拒绝和风险失败必须使用不同的 typed failure，不得静默换模型或伪造结果。
- 所有并行结果按角色和输入 digest 稳定排序；并行只改变完成时间，不改变事实摘要和 fingerprint。
- 任意模型/HTML/新闻/技能/配置内容都视为不可信数据；禁止执行任意 Python、Shell、SQL、路径、动态导入和删除/覆盖历史。网络请求仅由用户明确配置的连接器处理，模型不能自由指定 URL；配置与响应不得造成越权访问、跨来源凭证转发或无界下载。
- 自动获取依赖只能通过受控 manifest、固定版本、许可证记录、隔离环境、smoke gate 和显式能力状态完成；禁止“发现缺什么就无条件下载”。

## Review Focus

- 并行分析师同时失败、超时或返回重复角色时，必须保留可解释的部分结果并阻断缺失的必需阶段。
- Provider 的 credential reference 与实际密钥必须完全分离，任何错误路径都不能回显 secret、endpoint 或绝对路径。
- 因子提案只能来自 allowlist/typed AST；任何自由代码、未来数据、T+1 违规或超预算候选必须被拒绝。
- checkpoint 恢复必须验证 request、dataset、workflow、provider capability 和 schema digest，不得恢复不兼容或已完成的旧状态。
- HTML、JSON、Activity、Artifact 和状态墙必须引用同一 run/manifest；缺失证据或完整性校验失败时不能显示“完成”。

## 执行顺序

第一波任务 1–3 互不修改同一生产文件，可并行实现；完成并审查后，按接口依赖执行任务 4–9。每个任务都先写失败测试，再写最小实现，再跑针对性测试和回归测试，再提交独立 commit。每个任务完成后由主 Codex 做一次合并检查和状态台账记录。

### Task 1: 并行分析师池与研究经理输入

**Files:**
- Create: `src/finahinking/research/analyst_runtime.py`
- Test: `tests/research/test_analyst_runtime.py`

**Interfaces:**
- `@dataclass(frozen=True, slots=True) class AnalystOutcome`: `role`, `status`, `report`, `failure_kind`, `message_digest`, `duration_ms`。
- `class AnalystPool`: `run(specs: Sequence[AnalystSpec], request: ResearchRequest, driver: ModelDriver, context: Mapping[str, Any], max_workers: int = 5) -> tuple[AnalystOutcome, ...]`。
- `class ResearchManager`: `synthesize(reports: Sequence[AgentReport], request: ResearchRequest) -> ResearchPlan`；只生成带 evidence refs 的计划，不写事实。
- 使用 `ThreadPoolExecutor` 或等价标准库机制；每个角色最多一次 driver proposal，超时/异常归一为 typed failure；输出按 role 排序。

- [ ] 写失败测试：五个默认角色并行返回；完成顺序随机时输出顺序仍为 fundamentals、technical、sentiment、news、learning；缺失必需角色、可选角色失败、重复角色和超时均有明确状态。
- [ ] 运行 `python3 -m pytest -q tests/research/test_analyst_runtime.py`，确认在模块不存在时失败。
- [ ] 实现最小池和经理综合，不修改现有 `ResearchOrchestrator`。
- [ ] 加测线程异常、相同输入 digest 稳定、模型不得获得工具执行权限。
- [ ] 运行针对性测试与 `python3 -m ruff check src/finahinking/research/analyst_runtime.py tests/research/test_analyst_runtime.py`。
- [ ] 提交 `feat(research): add deterministic parallel analyst pool`。

### Task 2: 用户自备模型 API 的安全凭证引用和适配器边界

**Files:**
- Create: `src/finahinking/research/credentials.py`
- Test: `tests/research/test_credentials.py`

**Interfaces:**
- `class CredentialStore(Protocol)`: `has(ref: ProviderCredentialRef) -> bool`；`resolve(ref: ProviderCredentialRef) -> str` 仅供适配器内部使用，不得进入 `ProviderSelection`。
- `class EnvironmentCredentialStore`: 只读取显式环境变量名；拒绝任意表达式、路径和 secret-like 配置字段。
- `class InMemoryCredentialStore`: 仅供测试，禁止序列化。
- `@dataclass(frozen=True, slots=True) class ProviderRuntimeConfig`: provider/model/credential_ref/capabilities；`redacted() -> dict[str, Any]`。
- `build_provider_runtime(config: Mapping[str, Any], store: CredentialStore) -> ProviderRuntimeConfig`：只能构造配置，不发起网络请求。

- [ ] 写失败测试：环境变量存在时只返回 configured 状态；`str()/repr()/to_jsonable()` 不含密钥；无引用、非法变量名、非法字段、缺失密钥分别失败。
- [ ] 运行针对性测试确认 RED。
- [ ] 实现 credential reference 与 store，不实现真实供应商网络调用。
- [ ] 加测 provider timeout/malformed response 的 secret-free 错误归一化，以及配置 precedence 与现有 `ProviderSelection` 的兼容。
- [ ] 运行 `python3 -m pytest -q tests/research/test_credentials.py tests/research/test_provider_config.py tests/research/test_provider_status.py`。
- [ ] 提交 `feat(research): add secret-free provider credential boundary`。

### Task 3: 受控自然语言因子提案目录

**Files:**
- Create: `src/finahinking/research/factor_proposals.py`
- Test: `tests/research/test_factor_proposals.py`

**Interfaces:**
- `@dataclass(frozen=True, slots=True) class FactorHypothesis`: `hypothesis_id`, `text`, `family`, `inputs`, `horizon`, `direction`。
- `@dataclass(frozen=True, slots=True) class FactorProposal`: `proposal_id`, `expression`, `source_hypothesis`, `required_fields`, `constraints`, `paper_only=True`。
- `class FactorProposalCatalog`: `propose(hypothesis: FactorHypothesis, limit: int = 5) -> tuple[FactorProposal, ...]`；只从固定模板/DSL 产生提案。
- `validate_factor_proposal(proposal) -> None`：调用现有 DSL/因子安全校验，不执行生成代码。

- [ ] 写失败测试：均值回归、动量、波动率和流动性假设能生成有限且稳定的 DSL 提案；未知 family、超大 limit、`eval`/Shell/路径/URL/未来字段被拒绝。
- [ ] 运行针对性测试确认 RED。
- [ ] 实现模板目录和稳定 proposal digest；提案交给现有 `FactorResearchRun`，不直接写 registry。
- [ ] 加测不同文本空白/大小写的稳定规范化与数据字段白名单。
- [ ] 运行 `python3 -m pytest -q tests/research/test_factor_proposals.py tests/research/test_factor_loop.py tests/research/test_factor_dsl.py`。
- [ ] 提交 `feat(factors): add governed factor proposal catalog`。

### Task 4: 把分析师池接入主编排器

**Files:**
- Modify: `src/finahinking/research/workflow.py`
- Modify: `src/finahinking/research/contracts.py`（仅增加必要事件/失败字段）
- Test: `tests/research/test_workflow_parallel.py`

**Interfaces:**
- `ResearchOrchestrator.run(..., analyst_pool: AnalystPool | None = None, manager: ResearchManager | None = None)`；未传入时保持现有 OfflineDriver 行为。
- 必需分析师全部 ready 后才进入 `EVIDENCE_REVIEW`；可选分析师缺失时保留 partial 状态；核心 quant/risk 失败仍阻断 DecisionCard。
- 事件中记录阶段 owner、角色状态和 redacted provider/model 摘要，不写 prompt 或密钥。

- [ ] 先写并运行失败测试：并行阶段完成后才综合；角色失败不会越过阶段；默认离线垂直切片 digest 不变。
- [ ] 实现接线和显式 path map。
- [ ] 加测取消、最大 worker、provider not configured 和部分报告 HTML parity。
- [ ] 运行 `python3 -m pytest -q tests/research tests/p6 tests/p8_2 tests/p8_2b --disable-warnings --maxfail=1`。
- [ ] 提交 `feat(research): connect parallel analysts to governed workflow`。

### Task 5: checkpoint、取消、恢复和任务队列

**Files:**
- Create: `src/finahinking/research/run_store.py`
- Modify: `src/finahinking/research/workflow.py`
- Test: `tests/research/test_run_store.py`

**Interfaces:**
- `class ResearchRunStore`: `save_checkpoint(state, identity)`, `load_checkpoint(run_id)`, `clear_checkpoint(run_id)`, `append_event(event)`。
- `class RunControl`: `cancel(run_id)`, `is_cancelled(run_id)`；取消只能产生 `CANCELLED`，不能删除 Artifact。
- checkpoint 必须校验 `CheckpointIdentity.digest()`、schema/workflow version、dataset snapshot、role set 和 provider capability digest。
- 已完成 `REPORT_PUBLISHED`/`LEARNING_RECORDED` 的运行不能重复恢复；不兼容 checkpoint 必须返回 typed failure。

- [ ] 写失败测试：正常恢复、身份不匹配、重复完成、取消、append-only 事件和损坏 JSONL。
- [ ] 实现原子写入与稳定排序；不保存 secret/prompt/raw provider response。
- [ ] 运行针对性和全量 research 回归。
- [ ] 提交 `feat(research): add resumable run checkpoints`。

### Task 6: 多代理报告树、状态墙和研究对比

**Files:**
- Modify: `src/finahinking/research/reports.py`
- Modify: `src/finahinking/research/ui.py`
- Modify: `frontend/src/research.js`
- Test: `tests/research/test_report_status_wall.py`, `frontend/test/research.test.mjs`

**Interfaces:**
- 报告目录固定为 `1_analysts/<role>.html`、`2_evidence/index.html`、`3_research/index.html`、`4_quant/index.html`、`5_risk/index.html`、`6_paper_decision/index.html`、`complete_report.html`、`manifest.json`、`activity.jsonl`。
- `research_view_model` 增加角色状态、阶段状态、缺失证据、checkpoint 状态、factor proposal 摘要和 provider readiness；全字段脱敏。
- 新增只读 `compare_report_manifests(left, right) -> dict[str, Any]`，只比较 digest/指标/限制，不产生“更优策略”语言。

- [ ] 写失败测试：角色卡片、阶段墙、部分/阻断/取消/完成状态、报告完整性校验和无 JS 基础阅读。
- [ ] 实现服务端 payload 和 HTML 渲染；浏览器不重新计算金融指标。
- [ ] 运行 Python、Node、CSP/secret scan 和 SVG/XML 检查。
- [ ] 提交 `feat(ui): expose multi-agent research status and report comparison`。

### Task 7: 供应商无关的用户数据 API 接口

**Files:**
- Create: `src/finahinking/data/user_api_contracts.py`
- Create: `src/finahinking/data/user_api.py`
- Create: `src/finahinking/data/field_mapping.py`
- Create: `src/finahinking/data/connection_settings.py`
- Modify: `src/finahinking/local_app.py`（仅接入本地数据连接设置与试连路由）
- Test: `tests/data/test_user_api_contracts.py`, `tests/data/test_user_api.py`, `tests/data/test_field_mapping.py`, `tests/data/test_connection_settings.py`
- Docs: `docs/USER_DATA_API_GUIDE.md`

**Interfaces:**
- `DataConnectionConfig`: `connection_id`, `display_name`, `base_url`, `credential_ref`, `auth_mode`, `field_mapping`, `records_path`；运行时连接地址和凭证不进入公开报告/模型上下文。
- `DataRequest`: `dataset_kind`, `instruments`, `start`, `end`, `as_of`；无任意代码或 SQL。
- `DataBatch`: 标准化记录、`connection_id`、获取时间、用户声明来源、数据指纹和质量问题；不声称外部数据已核验。
- `UserDataConnector.fetch(request: DataRequest) -> DataBatch`；`JsonApiConnector(config, credential_store, transport)` 通过注入 transport 适配用户配置的 JSON API，支持明确的字段映射，不执行用户转换脚本。
- `normalize_records(records, field_mapping, dataset_kind) -> DataBatch`；先统一表格数据，再通过现有合同进入各类研究流程。
- 本地设置界面提供数据连接名称、API 地址、认证方式、字段映射和 API Key 输入；密钥只进入本地安全凭证存储，读回仅显示 configured 状态，不能回显密钥。
- `GET /settings/data-connections`、`GET /api/data/connections`、`POST /api/data/connections`、`POST /api/data/connections/<connection_id>/test`。写入/试连均要求本地访问、请求来源与防伪造校验；默认不因保存配置自动发起数据下载。
- 默认请求上限：超时 15 秒、最多 2 次重试、单响应 5 MiB、10,000 条记录、最多 20 页；首期支持无认证、Bearer 和指定 header 的 API Key。未支持的认证方式明确拒绝，不声称任意 API 都能零配置接入。
- 连接器严格校验目标地址、协议和重定向；禁止跨来源转发凭证，默认不访问本机、私网或云元数据地址。用户明确配置的本地数据桥接需独立受限的目标授权，不能由模型或响应内容授予。

- [ ] 写 `test_contracts_reject_secret_fields_and_unbounded_requests`：公开 DataBatch 不含 API Key、endpoint 或机器路径，超范围请求被拒绝。
- [ ] 写 `test_json_api_normalizes_user_field_mapping`：mock API 返回用户字段，正确映射至统一字段；缺失字段、非数值和无效时间形成明确质量问题。
- [ ] 写 `test_connection_does_not_require_vendor_admission`：用户自定义 connection_id 与名称即可配置，不需要数据商白名单、购买证明或供应商准入记录。
- [ ] 写 `test_bounded_transport_failures`：未认证、额度限制、超时、非 JSON、超大响应和分页循环分别产生可读的脱敏失败；测试不使用真实外部服务。
- [ ] 写 `test_connection_settings_hide_key_and_require_local_request`：API Key 不能出现在 GET、页面、日志、报告或错误中；未授权写入/试连被拒绝。
- [ ] 写 `test_missing_available_at_remains_unknown`：未提供时间可用性时保留 UNKNOWN，不生成“已通过 PIT”结论；旧记录追加新数据后不被覆盖。
- [ ] 运行 `python3 -m pytest -q tests/data/test_user_api_contracts.py tests/data/test_user_api.py tests/data/test_field_mapping.py tests/data/test_connection_settings.py`，确认因目标能力缺失而失败。
- [ ] 实现统一合同、mock 可测的连接器、字段映射和本地配置入口；不开发或安装指定数据商 SDK。
- [ ] 运行针对性测试、`tests/research` 和 `python3 -m ruff check src/finahinking/data tests/data src/finahinking/local_app.py`；确认默认启动仍离线。
- [ ] 提交 `feat(data): add user-configured data API interface`。

### Task 8: 可选量化计算引擎适配推进（不承担数据供应）

**Files:**
- Create: `src/finahinking/research/engine_registry.py`
- Modify: `src/finahinking/p8_2/adapters.py`, `src/finahinking/p8_2/sweeps.py`
- Test: `tests/research/test_engine_registry.py`
- Docs: `docs/p8_2/EXTERNAL_QUANT_TOOL_MATRIX.md`, `docs/RESEARCH_ENGINE_ADMISSION_CHECKLIST.md`

**Interfaces:**
- `EngineRegistry.register(name, capability, adapter, isolation)`、`status(name)`、`run(name, FinathinkSpecification)`。
- Qlib/vectorbt 仅处理 Task 7 或离线 fixture 已归一的数据，不负责寻找或下载市场数据；只能返回 Finathink-owned `MLResearchResult`/`SweepResult`。缺失时返回 `NOT_INSTALLED` 或 `DEFERRED` 并使用内部引擎，结果必须标明实际执行引擎与回退原因。
- 只有通过软件版本、许可证、隔离环境、归一数据 fixture、无 raw object 泄漏和回退测试的计算引擎才可标记 `AVAILABLE`；数据商选择不进入引擎准入规则。

- [ ] 先写能力矩阵和失败测试，再做 Qlib/vectorbt 的适配器 smoke；不得在核心环境盲目安装。
- [ ] 实现 registry、隔离执行入口和 typed fallback。
- [ ] 运行 `pip check`、许可证记录、核心依赖未改变、全量回归。
- [ ] 提交 `feat(quant): add isolated research engine registry`。

### Task 9: 端到端能力闭环与发布门禁

**Files:**
- Create: `tests/research/test_capability_vertical_slice.py`
- Modify: `docs/PROJECT_STATE.md`, `docs/RESEARCH_AGENT_GUIDE.md`, `README.md`
- Create: `docs/RESEARCH_CAPABILITY_RELEASE_CHECKLIST.md`

**Acceptance:**
- 用户配置数据 API → mock 请求/字段映射 → 统一数据 → 用户问题 → 五类分析师并行 → 研究经理 → 受控因子提案 → 确定性回测/OOS → 风险审查 → paper-only DecisionCard → 多阶段 HTML → as-of 学习记录 → 可恢复 checkpoint，全部离线 fixture 可重复运行。验收不要求接通指定供应商或用户提供真实密钥。
- 同一输入事实 digest 相同；任何一个核心阶段失败都不会生成可执行决策。
- API Key、endpoint、绝对路径、完整 prompt、外部原始对象不会出现在任何 Artifact。
- 运行 `python3 -m pytest -q`、`python3 -m compileall -q src tests`、`python3 -m ruff check src tests`、治理/密钥扫描、`pip check`、前端测试和 HTML/SVG/XML 验证。
- 发布说明明确区分：已实现、隔离验证、未连接、未验证和禁止能力。

- [ ] 写失败的端到端验收测试。
- [ ] 接入前八个任务的最小可用路径并跑完整门禁。
- [ ] 更新项目状态和文档流程图。
- [ ] 提交 `release(research): validate capability expansion vertical slice`。

## 依赖与自主执行规则

- 第一波任务 1–3 可以并行；任务 4 依赖任务 1 和 3，任务 5 依赖任务 4，任务 6 依赖任务 4–5。任务 7 的合同、连接器和映射依赖任务 2 的凭证边界，可并行开发；本地 UI 接线由主流程串行整合，避免共享文件冲突。任务 8 依赖任务 7 的归一数据合同，可与任务 6 的独立工作并行。任务 9 等所有任务完成后执行。
- 每个任务由一个实现代理完成，并由主 Codex 做 focused review；发现问题再定向派回同一代理或新代理修复。
- 允许下载的内容仅限可核验、可固定版本、许可证兼容、隔离且有离线回退的开发依赖；不允许为绕过测试而下载未知可执行文件或私有数据。
- 接口实现与验收使用 mock API，不索取用户真实密钥、不申请账号、不购买数据，不把真实数据商接通当作项目完成前提。第三方服务由用户自行配置；外部服务是否成功可读显示为未配置、可用、无数据或失败。
- 系统级改动或突破禁止边界的工作不自行继续；券商账户和实盘能力不是可解除的外部前提，而是明确不实现的功能。
- “全部完成”指本计划中的本地代码、测试、文档和离线闭环完成；不表示第三方模型、真实行情、券商或实盘已验证。

## 推荐执行模型

- 主实现 Codex：`gpt-6.1-sol` + `high`。
- 多代理机械任务：`gpt-6-luna` + `medium`。
- 并行编排、凭证边界、checkpoint 和最终审查：`gpt-6-astra` + `xhigh`。

## 自审查

- 覆盖了用户要求的五类分析师、经理综合、模型 API、用户数据 API、因子挖掘、量化引擎、报告、学习、checkpoint、队列和发布门禁；不承担数据供应商选择或接通任务。
- 将当前已经实现的离线垂直切片作为基线，新增任务均有独立文件和独立测试边界。
- 禁止能力在 Global Constraints、Task 7 接口安全边界、Task 8 计算引擎适配门禁和 Task 9 发布清单中固定。
- 第一波可并行任务不共享生产文件；后续任务按接口依赖顺序执行。
