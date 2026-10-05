# Task 4 状态报告：并行分析师接入主编排器

状态：完成

提交：`484581e952d952735e9f6b5d8fc54325ecc248c9` (`feat(research): connect parallel analysts to governed workflow`)

实现内容：

- `ResearchOrchestrator.run` 新增 `analyst_pool` 与 `manager` 接口；传入时走 AnalystPool → 必需角色门禁 → Evidence Review → ResearchManager → quant/risk，未传入时保留原 OfflineDriver 路径。
- 新增并行 worker 上限、取消处理、缺失必需角色、可选角色 partial、provider-not-configured、quant/risk typed failure。
- `RunEvent` 增加安全 metadata，记录阶段 owner、角色状态和脱敏 provider/model 摘要；事件不保存 prompt 或密钥。
- 新增 `tests/research/test_workflow_parallel.py`，覆盖并行完成顺序、阶段阻断、partial、provider、quant/risk、最大 worker、取消及事件 metadata。

验证：

- `python3 -m pytest -q tests/research/test_workflow_parallel.py`：7 passed
- `python3 -m pytest -q tests/research tests/p6 tests/p8_2 tests/p8_2b --disable-warnings --maxfail=1`：215 passed, 1 skipped
- `python3 -m ruff check src/finahinking/research/workflow.py src/finahinking/research/contracts.py tests/research/test_workflow_parallel.py`：passed

concerns：

- Task 5 的 checkpoint/恢复尚未接入；取消目前覆盖分析师池边界，持久化取消由后续任务处理。
- 目标 worktree 未检测到其他未提交变更，未发生共享 index 冲突。
