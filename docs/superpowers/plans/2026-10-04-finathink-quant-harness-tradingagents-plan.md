# Finathink Quant Harness + TradingAgents Implementation Plan

## Goal

在不引入真实交易、券商连接或外部模型运行时依赖的前提下，把已批准的设计落成一个可交给 Codex 分阶段执行的实现计划：

1. 用 Finathink 现有的确定性数据、因子、回测、风险与审计能力作为唯一事实层。
2. 增加一个受约束的研究代理编排层，能够接入 Codex 当前会话、离线驱动和用户自备 API 驱动。
3. 将多角色研究意见、量化验证、风险审查、纸面决策和学习记录统一为可序列化状态。
4. 生成可追溯的 HTML 报告包；HTML 只是阅读层，JSON、Artifact、DatasetSnapshot 和审计事件才是事实来源。
5. 通过离线垂直切片、确定性指纹和安全测试证明流程可重复、可拒绝越权请求、可解释失败。

## Architecture

```text
ResearchRequest
      |
      v
ProviderRegistry ---- ModelDriver (Offline/Codex envelope/User API)
      |                         |
      +------ ResearchOrchestrator ------+
      |          |      |       |        |
      |          |      |       |        +--> LearningStore (as-of, append-only)
      |          |      |       +----------> Risk review / paper decision
      |          |      +------------------> Finathink typed tool gateway
      |          +-------------------------> Analyst reports / evidence review
      +------------------------------------> Checkpoint identity
                                                |
                                                v
                                      JSON truth + HTML report bundle
```

Finathink 的 `src/finahinking/quant/services.py`、`src/finahinking/p6/gateway.py`、P5/P6 回测实现和现有数据模型继续拥有执行权。新层只允许通过显式、类型化的工具请求调用它们；任何模型输出都不能直接执行 Python、SQL、shell、路径、网络或经纪商动作。

## Tech Stack

- Python 3.11+，标准库 `dataclasses`、`enum`、`typing`、`json`、`html`、`concurrent.futures`。
- 复用当前 NumPy、pandas、pytest、ruff；不新增 LangGraph、Backtrader、DeepSeek SDK、OpenAI SDK 或其他 provider SDK。
- 现有 Finathink typed gateway、Dataset/Provenance、P5/P6 回测和 P7/P8.2b 本地应用。
- HTML 使用受控模板函数和标准库转义，不引入新的模板引擎。
- JSONL 事件、JSON manifest、不可变 dataclass 和稳定排序用于审计与确定性指纹。

## Spec

实现必须对应已批准的设计文档：

`docs/superpowers/specs/2026-10-04-finathink-quant-harness-tradingagents-design.md`

### Required contracts

- `ResearchRequest`：instrument、as_of、research_plan、analyst_roles、asset_class、workflow_version、config_digest。
- `ProviderSelection`：provider/model/role mapping/capabilities；序列化和报告中只能出现脱敏后的选择信息。
- `AgentReport`：role、status、claims、evidence_refs、limitations、model_ref、finished_at。
- `ResearchPlan`：hypotheses、required_datasets、factor_ids、validation_spec、risk_policy_version。
- `RunEvent`：event_id、run_id、state、actor、timestamp、payload_digest、severity。
- `ResearchRunState`：当前状态、状态历史、部分分析、工具调用摘要、失败分类、decision eligibility。
- `DecisionCard`：paper-only action/weights/rationale/evidence/limitations/approval requirement。
- `ReportManifest`：run_id、artifact paths、content digests、schema version、source snapshot、created_at。
- `CheckpointIdentity`：instrument/as_of、DatasetSnapshot、analyst set、role-model map、skill/workflow versions、depth/rounds/config digest、ResearchPlan digest。

### Required workflow states

主路径：`RECEIVED → IDENTIFIED → DATA_CHECKED → ANALYSTS_RUNNING → ANALYSTS_READY → EVIDENCE_REVIEW → RESEARCH_PLAN_READY → QUANT_VALIDATION → RISK_REVIEW → PAPER_DECISION_READY → REPORT_PUBLISHED → LEARNING_RECORDED`。

终止或拒绝状态：`REJECTED`、`NO_DATA_AVAILABLE`、`DATA_UNAVAILABLE`、`PROVIDER_NOT_CONFIGURED`、`VALIDATION_FAILED`、`CANCELLED`、`FAILED`。

### Required security and governance

- 模型、新闻、技能、HTML、配置都视为不可信输入。
- 禁止任意代码、任意路径、任意 SQL、任意 subprocess、任意网络和凭证传播。
- 研究运行只产生研究/纸面输出；不产生买卖委托，不连接券商，不声称投资建议。
- 核心数据、量化、风险失败时不得进入 `PAPER_DECISION_READY`。
- 可选分析师失败可以保留部分分析，但必须明确缺失和局限。
- 所有重复运行使用稳定输入、稳定排序和确定性摘要；动态时间只进入事件元数据，不进入事实摘要。

## Global Constraints

1. 不复制两个参考压缩包的运行时代码；仅吸收其架构模式、报告结构、provider 路由、checkpoint、as-of memory 和多角色研究流程。
2. 不把 DeepSeek 或 TradingAgents 设为硬依赖；provider 只是可插拔适配器，当前 Codex 会话只能通过显式 envelope/handoff 进入，不能被本地服务隐式调用。
3. 旧的 Finathink 公开 API、现有回测语义、P5/P6 权限边界和现有测试必须保持兼容。
4. 不向模型暴露 API key、token、endpoint、绝对路径、数据库密码或内部凭证；日志、报告、checkpoint、错误信息同样不得含秘密。
5. `PAPER_DECISION_READY` 不代表可交易；UI、报告和类型名称都必须带 `paper-only`/研究用途语义。
6. 新功能必须有 feature flag 或显式入口；默认启动路径仍保持当前离线 Finathink 行为。
7. 每个任务先写失败测试，再写最小实现，再运行针对性测试；不能用放宽断言、跳过测试或大范围重构代替修复。
8. 每阶段结束都运行 `python3 -m pytest ...`、`python3 -m compileall src tests` 和 `python3 -m ruff check ...`；任何未验证项要在交付说明中列出。
9. 不实现高频数据、实时行情、实盘执行、自动下单、投资组合托管或用户风险承受能力判断。

## Review Focus

- 合同是否不可变、JSON-safe、可版本化，旧 `FactorDefinition`/P5/P6 API 是否兼容。
- 工具是否只允许当前 Finathink allowlist，是否拒绝代码、路径、SQL、凭证和未知操作。
- 状态机是否有上限、失败是否可解释、核心失败是否阻断纸面决策、分析师并行是否仍可复现。
- HTML、JSON、Artifact、事件和 checkpoint 是否互相校验，是否能从 manifest 追溯到 DatasetSnapshot。
- as-of 学习、T+1、OOS、成本/滑点和风险规则是否仍由确定性引擎判定，而不是由模型自报。
- 测试是否包含恶意输入、秘密泄漏、时间穿越、重复运行指纹、provider 未配置和部分分析失败。

## Repository map before editing

先确认以下现有文件的实际接口和测试，再按任务增量编辑；不得假设摘要之外的字段：

- `src/finahinking/factors/core.py`：保留现有 `FactorDefinition`、`momentum_factor`、`evaluate_factor`，仅做向后兼容扩展。
- `src/finahinking/data/models.py`：复用 `Dataset`、`Provenance`，不复制数据来源模型。
- `src/finahinking/quant/services.py`：复用量化 allowlist 和 typed service，不开新任意调用入口。
- `src/finahinking/p6/gateway.py`、`src/finahinking/p6/state_machine.py`、`src/finahinking/p6/workflows.py`：复用 P6 权限和 guided workflow 语义。
- `src/finahinking/local_app.py`、`frontend/src/research.js`、`frontend/test/research.test.mjs`：在 Phase E 接入只读研究状态与报告入口。
- `pyproject.toml`：只在确有需要时加入包数据或脚本入口，不加入 provider SDK。

## Implementation tasks

### Task 1 — 建立 research 包和不可变合同

Files to create:

- `src/finahinking/research/__init__.py`
- `src/finahinking/research/contracts.py`
- `tests/research/__init__.py`
- `tests/research/test_contracts.py`

Interfaces:

- `class ResearchState(str, Enum)`：主路径和终止状态。
- `class FailureKind(str, Enum)`：`NO_DATA_AVAILABLE`、`DATA_UNAVAILABLE`、`DATA_INVALID`、`PROVIDER_NOT_CONFIGURED`、`VALIDATION_FAILED`、`TOOL_REJECTED`、`INTERNAL_ERROR`。
- `@dataclass(frozen=True) class ResearchRequest`：`run_id`, `instrument`, `as_of`, `research_plan`, `analyst_roles`, `asset_class`, `workflow_version`, `config_digest`，构造时校验非空、日期格式和角色稳定排序。
- `@dataclass(frozen=True) class ProviderSelection`：provider/model/role map/capabilities，`redacted()` 不返回 key、endpoint、path。
- `@dataclass(frozen=True) class AgentReport`、`ResearchPlan`、`RiskReview`、`DecisionCard`、`RunEvent`、`ResearchRunState`、`CheckpointIdentity`、`ReportManifest`。
- `to_jsonable(value) -> dict[str, Any]`：只接受白名单 dataclass、enum、日期、mapping、序列；拒绝 callable、bytes、Path 和未知对象。
- `stable_digest(value) -> str`：canonical JSON + SHA-256，字段顺序稳定。

Tests first:

1. 合同可 round-trip 为 JSON 且 digest 对字段顺序不敏感。
2. 非法状态转移输入、空 instrument、逆序 as-of、重复角色和未知字段被拒绝。
3. `redacted()` 和 `to_jsonable()` 不包含 secret-like key 名、endpoint、绝对路径或 callable。
4. `CheckpointIdentity` 能稳定包含 DatasetSnapshot、ResearchPlan 和配置摘要。

Commands and expected output:

```bash
python3 -m pytest -q tests/research/test_contracts.py
```

Expected: new tests pass; existing `tests/quant` and `tests/p5_5` remain unchanged and passing.

Commit checkpoint: `feat(research): add versioned immutable research contracts`

### Task 2 — Provider registry、模型驱动和 Codex handoff

Files to create:

- `src/finahinking/research/providers.py`
- `src/finahinking/research/drivers.py`
- `tests/research/test_providers.py`
- `tests/research/test_drivers.py`

Interfaces:

- `@dataclass(frozen=True) class ProviderCapabilities`：structured_output、tool_calling、parallel_roles、max_context、offline。
- `class ProviderAdapter(Protocol)`：只暴露 `capabilities()` 和 `invoke(envelope: ModelEnvelope) -> ModelResponse`；不接收裸 prompt 中的密钥。
- `class ProviderRegistry`：`register(name, adapter)`, `resolve(selection)`, `check(selection, required_capabilities)`, `redacted_selection(selection)`。
- `class ModelDriver(Protocol)`：`propose(request: ResearchRequest, context: Mapping[str, Any]) -> DriverResult`。
- `class OfflineDriver`：从固定 fixture 生成确定性角色报告/研究计划，明确标记 `offline`。
- `class CodexInteractiveDriver`：只生成 `CodexPlanEnvelope`（可复制、可审查、可回传），不尝试访问当前 Codex 会话的内部 API。
- `class UserApiDriver`：只接收外部实现的 `ProviderAdapter`，缺失 provider 时返回 `PROVIDER_NOT_CONFIGURED`，不静默切换。
- `class CompatibleApiDriver`：预留 OpenAI-compatible/DeepSeek-compatible 适配边界，但 Phase A 只做接口和拒绝路径，不安装 SDK。

Tests first:

1. provider 未注册、能力不足和模型未配置分别产生 typed failure。
2. provider precedence 为 defaults → local config → env → CLI/UI → per-run override；任何 key 不进入 `ProviderSelection`、日志或 envelope。
3. offline driver 在相同 request/context 下两次 digest 相同。
4. Codex driver 输出可审查 envelope，不能执行工具、不能访问文件/网络、不能声明已完成模型调用。
5. `UserApiDriver` 只在显式提供 adapter 时工作，不能从环境变量自动读取秘密值。

Commands:

```bash
python3 -m pytest -q tests/research/test_providers.py tests/research/test_drivers.py
```

Commit checkpoint: `feat(research): add provider capabilities and safe model drivers`

### Task 3 — 类型化研究工具网关

Files to create:

- `src/finahinking/research/tools.py`
- `tests/research/test_tools.py`

Files to modify:

- `src/finahinking/quant/services.py`（仅增加可复用的 typed adapter/export，不改变现有 allowlist 语义）
- `src/finahinking/p6/gateway.py`（仅在需要时增加研究层调用所需的公开、最小入口）

Interfaces:

- `class ResearchToolName(str, Enum)`：`research.inspect_dataset`、`research.resolve_instrument`、`research.compute_factor`、`quant.run_backtest`、`quant.run_regression`、`quant.evaluate_performance`、`quant.analyze_risk`、`quant.inspect_run`、`research.render_report`、`learning.inspect_asof_lessons`、`learning.record_evidence`。
- `@dataclass(frozen=True) class ResearchToolRequest`：name、typed args、run_id、request digest。
- `@dataclass(frozen=True) class ResearchToolResponse`：status、typed result、artifact refs、failure kind、provenance。
- `class ResearchToolGateway`：`execute(request) -> ResearchToolResponse`；只映射到现有 Finathink gateway/service，未知工具、任意 code/path/sql/subprocess/network 参数一律 `TOOL_REJECTED`。
- `validate_tool_args(name, args) -> None`：检查字段、类型、规模、日期和 run ownership。

Tests first:

1. 所有 allowlisted tools 能用最小 fixture 运行并返回 provenance。
2. `eval`, shell、SQL、绝对路径、`file://`、URL、callable、未知字段和超大参数被拒绝。
3. `run_id` 不匹配或重复执行不会越权读取其他 run。
4. 现有 quant/p6 测试的行为和错误类型保持不变。

Commands:

```bash
python3 -m pytest -q tests/research/test_tools.py tests/quant tests/p5_5
```

Commit checkpoint: `feat(research): expose governed typed tool gateway`

### Task 4 — 有界多角色研究编排器

Files to create:

- `src/finahinking/research/workflow.py`
- `tests/research/test_workflow.py`

Interfaces:

- `@dataclass(frozen=True) class AnalystSpec`：role、required/optional、driver、max_rounds、timeout。
- `class ResearchOrchestrator`：`run(request, driver, tools, provider_registry, analyst_specs, limits) -> ResearchRunResult`。
- `ResearchOrchestrator.run` 按状态机推进，并把每次状态变更写成 `RunEvent`；分析师可以并行，但结果按 role 排序后合并。
- `run_analyst(spec, request, context) -> AgentReport`：bounded call count；不得执行未授权工具。
- `review_evidence(reports, tools) -> ResearchPlan`：只引用已有 evidence refs，不能凭空创建数据。
- `run_risk_review(plan, quant_result) -> RiskReview`：确定性风险门槛优先，模型解释只能作为说明。
- `make_paper_decision(risk_review, reports, quant_result) -> DecisionCard`：核心失败时抛出/返回不可决策状态。

Required behavior:

- 基本面、技术/市场、情绪/资金、新闻/宏观、学习五类角色为默认角色集。
- 可选角色失败时保留 `partial_analysis` 和 limitation；核心数据/量化/风险失败时不可进入 `PAPER_DECISION_READY`。
- 每类 round、tool round、risk round、总耗时有上限。
- provider 未配置、无数据和数据不可用分别映射到不同终止状态。
- 状态快照和 event payload 只能保存摘要/digest，不保存 prompt、完整新闻、密钥或内部路径。

Tests first:

1. happy path 完整走到 `LEARNING_RECORDED`，且状态历史无跳跃。
2. optional analyst failure 生成部分结果；核心工具失败阻断 paper decision。
3. provider 未配置、无数据、无效数据、超轮次、取消和重复 run 各有独立结果。
4. 相同 offline inputs 两次得到相同 report/decision/fingerprint；并行与串行合并顺序一致。
5. 任何模型返回的“已执行交易”声明都被归一为 paper-only 文本，不改变权限。

Commands:

```bash
python3 -m pytest -q tests/research/test_workflow.py
```

Commit checkpoint: `feat(research): add bounded multi-role research workflow`

### Task 5 — 因子注册、健康度和九步生命周期

Files to create:

- `src/finahinking/factors/registry.py`
- `tests/research/test_factor_registry.py`

Files to modify:

- `src/finahinking/factors/core.py`：为现有 `FactorDefinition` 增加可选、默认兼容的 metadata/health 投影；不改变现有构造调用和 `evaluate_factor` 的 T+1 语义。

Interfaces:

- `class FactorHealthStatus(str, Enum)`：`VALID`、`DECAYING`、`REVERSED`、`INSUFFICIENT_DATA`、`RETIRED`。
- `@dataclass(frozen=True) class FactorMetadata`：id/version/definition/formula/input_fields/source/pit/direction/limits/validation_spec。
- `@dataclass(frozen=True) class FactorHealth`：status、as_of、ic、icir、decay_score、crowding_score、collinearity_score、sample_size、reason。
- `class FactorRegistry`：`register`, `get`, `list`, `update_health`, `select_eligible(as_of, constraints)`；所有版本和状态变更 append-only。
- `run_factor_lifecycle(factor, dataset_snapshot, validation_spec) -> FactorLifecycleResult`：hypothesis → compute → IC/ICIR → dedupe → T+1 → annual/OOS → orthogonal/capacity → archive/false，并输出每步 evidence refs。

Tests first:

1. 旧 momentum factor API 仍通过现有测试。
2. 缺 PIT/source/direction/validation 或 metadata version 回退时拒绝注册。
3. decay/reversed/insufficient data/retired 会从 eligible 集合中排除。
4. OOS 和 T+1 违规被识别；因子健康评估不会读取未来 as-of 数据。
5. 相同输入得到相同 factor health 和 lifecycle digest。

Commands:

```bash
python3 -m pytest -q tests/research/test_factor_registry.py tests/quant
```

Commit checkpoint: `feat(factors): add versioned registry and health lifecycle`

### Task 6 — 报告包、manifest 和事件审计

Files to create:

- `src/finahinking/research/reports.py`
- `tests/research/test_reports.py`

Interfaces:

- `class ReportBundleWriter`：`write(result, output_root) -> ReportManifest`。
- `render_section_html(title, payload, evidence_refs, limitations) -> str`：HTML escape、固定区块、无未转义模型文本。
- `write_manifest(manifest, path)`, `append_event(event, path)`：原子写入/追加，稳定 JSON 编码。
- `verify_report_bundle(manifest_path) -> BundleVerification`：校验所有引用文件 digest、manifest schema 和 required sections。

Required paths for every run:

```text
reports/<run_id>/complete_report.html
reports/<run_id>/manifest.json
reports/<run_id>/activity.jsonl
reports/<run_id>/1_analysts/{fundamentals,technical,sentiment,news,learning}.html
reports/<run_id>/2_evidence/
reports/<run_id>/3_research/
reports/<run_id>/4_quant/
reports/<run_id>/5_risk/
reports/<run_id>/6_paper_decision/
```

Tests first:

1. 每个 required path、manifest entry、digest 和 section 都存在并可验证。
2. `<script>`, attributes, URLs、news/model text 和错误字符串都正确转义或作为纯文本写入。
3. HTML 与 JSON/Artifact 的 claim/evidence/limitation 数量一致；manifest 发现缺失时失败。
4. report/log/checkpoint 中不出现 key、token、endpoint、绝对路径或完整 prompt。
5. 相同离线结果的事实部分 HTML/JSON 稳定；时间戳仅保留在元数据。

Commands:

```bash
python3 -m pytest -q tests/research/test_reports.py
```

Commit checkpoint: `feat(research): add auditable html report bundles`

### Task 7 — as-of 学习层和证据记录

Files to create:

- `src/finahinking/research/learning.py`
- `tests/research/test_learning.py`

Interfaces:

- `@dataclass(frozen=True) class LearningEntry`：entry_id、created_at、as_of、instrument_scope、lesson_type、claim、evidence_refs、source_run_id、status。
- `class LearningStore`：`record_evidence(entry)`, `inspect_asof_lessons(as_of, scope)`, `digest()`；写入 append-only JSONL/JSON store，禁止覆盖已有 entry。
- `validate_learning_entry(entry) -> None`：拒绝未来 as-of、无证据 claim、空 source run、秘密和未经脱敏文本。
- `reconcile_learning(run_id, reports, decision, as_of) -> tuple[LearningEntry, ...]`：只记录可追溯的结果、失败、风险和后验观察，不把模型猜测写成事实。

Tests first:

1. `inspect_asof_lessons` 不返回 as-of 之后的 entry。
2. duplicate entry、未来 entry、缺证据、秘密和路径注入被拒绝。
3. append-only：已有 entry 不会被更新覆盖；重复读取 digest 稳定。
4. workflow 在 `LEARNING_RECORDED` 只写入已发布 run 的 evidence。

Commands:

```bash
python3 -m pytest -q tests/research/test_learning.py
```

Commit checkpoint: `feat(research): add append-only as-of learning store`

### Task 8 — 第一条离线垂直切片

Files to create:

- `tests/research/test_vertical_slice.py`
- `docs/RESEARCH_AGENT_GUIDE.md`

Files to modify:

- `src/finahinking/research/__init__.py`：导出稳定的离线入口。
- `pyproject.toml`：仅在需要时注册 `finahinking-research` CLI；默认命令必须仍为离线/研究模式。

Implementation:

- 以现有 deterministic fixture/Dataset/Provenance 构造一个 instrument + as-of request。
- 使用 `OfflineDriver + ResearchToolGateway + ResearchOrchestrator + FactorRegistry + LearningStore + ReportBundleWriter` 完成一条完整流程。
- 同一输入执行两次，比较 `ResearchRunState`、decision、manifest content digests、learning digest；允许 created_at/activity timestamp 不同，但事实摘要必须相同。
- 文档写清楚 Codex handoff、用户自备 API、provider config precedence、paper-only 边界、报告目录和失败分类。

Tests first:

```bash
python3 -m pytest -q tests/research/test_vertical_slice.py
python3 -m pytest -q tests/quant tests/p5_5 tests/p8_2 tests/p8_2b --disable-warnings --maxfail=1
python3 -m compileall -q src tests
python3 -m ruff check src/finahinking/research tests/research
```

Expected: vertical slice runs twice with identical deterministic facts; current focused baseline remains 101 passed or higher only because of newly added tests, with no regression.

Commit checkpoint: `feat(research): prove offline end-to-end vertical slice`

### Task 9 — 研究状态只读 UI 和 HTML 入口（Phase E）

Only begin after Tasks 1–8 pass.

Files to create:

- `src/finahinking/research/ui.py`
- `tests/research/test_ui.py`

Files to modify:

- `src/finahinking/local_app.py`：增加只读研究 run/status/report routes，复用现有 HTML shell；不增加执行交易或直接 provider 调用。
- `frontend/src/research.js`：显示状态墙、角色完成度、evidence/limitation、quant/risk 摘要、paper decision 标签和报告链接。
- `frontend/test/research.test.mjs`：覆盖 loading → success → partial → blocked/error。

Interfaces:

- `research_view_model(run_state, manifest) -> dict[str, Any]`：只输出脱敏、稳定排序的 UI payload。
- `research_report_url(run_id, section) -> str`：只允许 manifest 中存在的相对 section。
- local app route：`GET /research/<run_id>`、`GET /research/<run_id>/status`、`GET /research/<run_id>/report/<section>`；未知 run/section 返回 typed 404/422，不读取任意路径。

UI acceptance:

- 明确显示 `OFFLINE`、`PAPER-ONLY`、as-of、数据状态、缺失分析师和限制。
- 可以打开完整 HTML 报告，但不能一键执行买卖。
- 无 JS 时仍能读取基础状态和报告链接；错误状态可读且不泄漏内部异常。

Commands:

```bash
python3 -m pytest -q tests/research/test_ui.py tests/p8_2 tests/p8_2b
node --test frontend/test/research.test.mjs
python3 -m ruff check src/finahinking/local_app.py src/finahinking/research
```

Commit checkpoint: `feat(ui): expose read-only research run status and reports`

### Task 10 — 用户 provider 适配边界和发布审计

Files to create:

- `docs/research-providers.example.json`
- `tests/research/test_provider_config.py`
- `docs/RESEARCH_RELEASE_CHECKLIST.md`

Files to modify:

- `src/finahinking/research/providers.py`：增加配置文件/环境变量/CLI/UI/per-run 的解析和验证，但只保留 redacted selection。
- `README.md` 或当前项目主 README：增加研究代理启用方式、API 自备说明、离线默认、无实盘声明。

Configuration rules:

- example file 只包含 provider 名称、能力、模型别名和启用状态；使用明显的 placeholder，不写真实 key、endpoint 或机器路径。
- environment/CLI/UI 只传入 secret reference，不把 secret value 写入 `ProviderSelection` 或报告。
- 未安装 SDK、能力不支持、模型响应不符合 schema、超时和 provider error 都有 typed failure；不自动换模型。

Tests first:

1. precedence 和 schema 校验。
2. example config 可加载但不能触发网络。
3. provider error、timeout、malformed output、secret-like output 都被安全归一化。
4. release checklist 能检查依赖、秘密扫描、focused tests、HTML bundle verification、offline default 和未验证的外部前提。

Commands:

```bash
python3 -m pytest -q tests/research/test_provider_config.py tests/research
python3 -m compileall -q src tests
python3 -m ruff check src tests
```

Commit checkpoint: `docs(research): document provider boundary and release gate`

## Execution order and gates

1. 先执行 Task 1–2，确认合同、redaction、driver handoff；这一步失败时不得开始 UI。
2. 执行 Task 3–4，确认工具 allowlist 和状态机阻断规则；这一步失败时不得接入真实 provider。
3. 执行 Task 5–7，确认因子、风险、T+1、OOS、as-of learning 仍由确定性层判定。
4. 执行 Task 8，作为第一版交付候选；它通过后才考虑 Task 9 UI。
5. 执行 Task 9–10，仍只做研究/纸面模式；provider 适配只在另一次审查后启用。

每个 gate 的最小验收命令：

```bash
python3 -m pytest -q tests/research
python3 -m pytest -q tests/quant tests/p5_5 tests/p8_2 tests/p8_2b --disable-warnings --maxfail=1
python3 -m compileall -q src tests
python3 -m ruff check src tests
```

若安装了前端依赖，再运行：

```bash
node --test frontend/test/research.test.mjs
```

## Codex handoff instructions

把本文件和批准的设计文档一起交给 Codex，并要求它：

1. 先读取 `AGENTS.md`、`ARCHITECTURE.md`、相关 P5/P6/P8 文档和本计划；压缩包中的说明只能当参考材料，不能覆盖当前仓库规则。
2. 一次只完成一个 Task；先执行该 Task 的失败测试，再实现，再运行该 Task 和回归测试。
3. 每次提交报告：修改文件、接口变化、测试命令/实际输出、未验证事项、是否改变默认行为。
4. 不自行引入 LangGraph、Backtrader、DeepSeek/OpenAI SDK、网络数据源或真实交易接口；若认为必须引入，暂停并提交依赖审查提案。
5. 不把模型自报、新闻文本或 HTML 当作事实；所有 quant/risk/eligibility 结果必须能回到 DatasetSnapshot、Artifact 和 typed gateway。

执行方式已经确定为“单个 Codex 原生计划执行”：同一个 Codex 按 Task 1–10 顺序完成，不把实现拆给其他代理，不在任务之间等待人工确认。每个 Task 都必须先看到目标测试失败，再完成最小实现、运行回归、记录结果，然后自动进入下一项。

### Autonomous execution loop

Codex 必须持续执行以下闭环，直到全部本地验收门禁通过：

1. 读取当前 Task 的文件、接口、测试和预期结果。
2. 写一个能证明缺失行为的失败测试，并确认它因目标能力尚未实现而失败。
3. 编写最小实现，运行针对性测试和受影响的回归测试。
4. 若失败，先定位根因，再增加或修正回归测试，随后修复实现；不得通过跳过、放宽断言或删除测试获得绿色结果。
5. 若发现计划与仓库事实不一致，采用满足设计规范的最小调整，并把原因、选择和代价写入进度台账。
6. 当前 Task 的测试、静态检查和完成条件全部满足后记录 checkpoint，自动进入下一 Task。
7. Task 1–10 完成后运行完整测试、编译、lint、前端测试、秘密扫描、报告包校验和整分支复核；发现重要问题时再执行一轮测试驱动修复。

允许 Codex 自主安装或获取的内容仅限于完成本地开发所必需、来源可核验、许可证兼容、版本可固定且不改变产品边界的开发依赖。安装前必须先检查仓库已有锁文件、可选依赖和本机能力，并记录新增依赖的用途、许可证、版本和替代方案。以下情况不得自行继续：需要 API key、账号登录、付费数据、真实资金/交易权限、系统级高风险改动、来源不明的可执行文件、许可证冲突，或需要突破本计划的安全边界。此类情况应保持离线替身继续完成其余可验证部分，并把外部前提列为明确的未验证项。

“完成”只表示：本仓库中计划范围内的代码和文档已经实现，所有可用的本地验收门禁通过，且外部前提被诚实标注；它不表示真实行情、第三方模型、券商或实盘交易已经验证。

## Recommended Codex model and reasoning strength

### Default recommendation for implementation

- Model: `gpt-6.1-sol`
- Reasoning strength: `high`
- Use: Task 1–10 的实际编码、测试、增量修复和回归；它足够强，且适合长时间多文件工程执行。

### Review/escalation recommendation

- Model: `gpt-6-astra`
- Reasoning strength: `xhigh`
- Use: 开始前审阅合同/安全边界，或在 provider、checkpoint、HTML/JSON parity、状态机出现争议时做一次独立审查；不建议让它在没有 gate 的情况下直接批量改完整仓库。

如果产品界面只允许一个模型/强度组合，选 `gpt-6.1-sol + high`。如果当前 Codex 运行可以按任务切换，采用“`gpt-6-astra + xhigh` 审查设计与 Task 1–2，`gpt-6.1-sol + high` 执行其余任务”的组合。

## Self-review of this plan

- Spec coverage：已覆盖 provider/driver、五类分析师、状态机、typed tools、因子九步、风险门禁、HTML 报告、as-of learning、checkpoint、UI、配置和发布门禁。
- Step scan：每个任务均给出文件路径、接口、测试先行步骤、命令、预期结果和提交检查点；任务按依赖顺序排列。
- Type consistency：`contracts.py` 是唯一跨模块事实合同；providers/drivers/tools/workflow/reports/learning 都只依赖合同，不复制 Dataset 或 quant 结果类型。
- Review focus coverage：工具拒绝、secret redaction、T+1/OOS/as-of、deterministic fingerprint、HTML parity、核心失败阻断均有专门测试任务。
- Proportion：Phase A–D 形成可交付离线垂直切片；UI 和真实 provider 明确后置，不把未验证外部能力混进第一版。
