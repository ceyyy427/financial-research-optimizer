# Task 9 实施报告：离线能力闭环与发布门禁

日期：2026-10-07
工作树：`codex/research-capability-roadmap`  运行目录：`/Users/mac/.codex/worktrees/research-agent-runtime/Finahinking Autonomous Builder`

## 结果

Task 9 在前八项实现之上补齐了一个可重复的离线端到端验收测试、发布状态文档和中文发布清单。验收链路使用注入的 mock JSON transport 和固定 fixture，不连接具体数据商、不读取真实密钥、不安装 SDK，也不实现 broker、order 或 live trading。

## 交付文件

- `tests/research/test_capability_vertical_slice.py`
  - 通过 `DataConnectionConfig`、显式字段映射和 `JsonApiConnector` 取得统一 `DataBatch`。
  - 将同一数据 fingerprint 注入研究工具上下文，再运行 fundamentals、technical、sentiment、news、learning 五类分析师并行池。
  - 由 `ResearchManager` 生成 evidence-indexed plan；因子假设通过固定 DSL 模板产生后，真实调用 `run_factor_research`，覆盖 train/validation 的 hidden OOS、冻结策略、test once-only 和 run fingerprint。
  - 因子运行直接消费字段映射后的完整 normalized records；其 run fingerprint 绑定到 quant request 的 `factor_ids`，quant spy 同时断言完整统一字段和值已进入研究上下文。
  - 量化 fixture 显式返回 deterministic engine 与 `oos=True`；data unavailable/no-data、quant、risk、provider-not-configured 和 required-analyst failure 矩阵均断言 `decision is None`、`decision_eligible is False` 且不进入 `PAPER_DECISION_READY`。
  - 生成 paper-only `DecisionCard`、多阶段 HTML/manifest/activity、as-of `LearningStore` 记录，并保存/加载带 identity、dataset、workflow 和 capability digest 的 checkpoint。
  - 对同一输入比较两次非时间性报告文件 digest，排除只含运行时间的 `activity.jsonl`。
  - 递归扫描 `reports/<run_id>`（含 manifest/activity/HTML）、`learning.jsonl` 和 `checkpoints/*.json`，确认 API key/token/secret/password/endpoint/prompt/raw provider response、绝对路径和 raw object 均不进入公开产物。
- `docs/PROJECT_STATE.md`
  - 更新 P8 capability-expansion 状态和发布边界矩阵。
- `docs/RESEARCH_AGENT_GUIDE.md`
  - 增加从用户数据接口到 checkpoint 的离线研究路径、PIT 和公开产物边界说明。
- `README.md`
  - 增加用户可见的离线能力扩展闭环和验收链接。
- `docs/RESEARCH_CAPABILITY_RELEASE_CHECKLIST.md`
  - 新建中文发布门禁，区分已实现、隔离验证、未连接、未验证和禁止能力。

## TDD 与验证证据

先创建端到端测试并运行针对性测试；首轮失败暴露了 manifest `source_snapshot` 使用 `date` 直接 JSON 编码的问题，随后将断言改为安全的结构化字段检查。增量 hardening 后的针对性测试：

```text
python3 -m pytest -q tests/research/test_capability_vertical_slice.py
3 passed
```

最终门禁：

```text
python3 -m pytest -q
557 passed, 1 skipped in 43.21s

python3 -m compileall -q src tests
passed

python3 scripts/validate_governance.py .
PASS: governance validation passed

python3 scripts/secret_scan.py
secret scan passed (no known credential patterns)

python3 -m pip check
No broken requirements found.

cd frontend && npm test
13 passed

HTML/SVG/XML parse check
parsed html=1 svg_xml=0

git diff --check
passed
```

`python3 -m ruff check tests/research/test_capability_vertical_slice.py` 通过。全量 `python3 -m ruff check src tests` 仍有两个 Task 3 既有问题，未在 Task 9 重写既有实现：

```text
src/finahinking/research/factor_proposals.py:11 F401 unused Sequence
src/finahinking/research/factor_proposals.py:20 FURB167 re.I alias (可机械修复)
```

这两个问题不影响 Task 9 针对性测试、全量 pytest、compileall、治理、secret、依赖或前端门禁；在最终发布记录中保留为 Ruff `UNVERIFIED/EXISTING` 项，不能把全量 Ruff 称为通过。

## 能力边界

已实现并由 fixture 验证：供应商无关的数据合同、字段映射、bounded connector、PIT unknown/available 表达、五角色并行池、研究经理、受控因子 proposal、确定性量化/OOS、风险阻断、paper-only DecisionCard、HTML 报告树、as-of learning 和可恢复 checkpoint。

隔离验证：`EngineRegistry` 只接收 Finathink-owned normalized data；可选引擎只有在版本、许可证、隔离、fixture、raw-object boundary、回退和受信 sandbox 全部满足时才可用，否则回退到内部确定性引擎。

未连接：具体数据商、真实用户 API、真实模型服务、QMT、券商、账户、订单、撤单和实时行情。

未验证：真实 credential 可用性、第三方 schema/额度、生产网络/DNS、浏览器 E2E、生产部署、外部 sandbox 和 optional-license admission。mock transport 不能证明这些事实。

禁止：公开 Artifact 中出现 secret、endpoint、绝对路径、完整 prompt 或 raw provider object；任意代码、Shell、SQL、动态 URL；broker/order/live trading；投资建议。

## Commit

原始 Task 9 提交：`59790ba`。本 hardening 由增量 commit 记录。Task 9 本身没有接通外部服务或改变真实数据来源。
