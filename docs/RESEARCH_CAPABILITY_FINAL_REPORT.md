# Research Capability Final Report

日期：2026-10-09  
范围：Task 17 最终发布门禁（本地、研究用途、离线优先）

## 结论

本 checkout 的可重放本地合同和前端测试通过；发布状态仍为
`CONDITIONAL`。最终判定按证据类别列出，不使用单一百分比掩盖失败、跳过或
外部未验证状态。

## OFFLINE_PASS

- `python3 -m compileall -q src tests`：exit 0。
- `python3 scripts/validate_governance.py .`：`PASS: governance validation passed`。
- `python3 -m pip check`：`No broken requirements found.`
- `cd frontend && npm test`：17 passed，0 failed。
- 本地数据合同、PIT/指纹、五类分析师、证据汇总、受控因子 DSL、回测/OOS、
  风险检查、纸面组合、队列恢复、checkpoint、报告树和学习提案均保持研究用途
  与人工准入边界。

## OFFLINE_BROWSER_PASS

- Task 16 的本地 Playwright/Chromium 验收为 `OFFLINE_BROWSER_PASS`：真实 loopback
  `create_server()`、内存研究数据和本机 Chromium 覆盖 no-JS、失败状态、secret
  masking、键盘焦点、报告/运行状态、桌面与 390px 移动布局、stream-fetch 错误和
  page/console error 检查；首次运行 `4 passed`，保存 7 个 HTML/PNG 证据文件及
  `SHA256SUMS.tsv`，且哈希校验通过。
- 可移植重跑在当前 checkout 因 Playwright bundled Chromium 未安装而明确跳过真实
  浏览器用例，HTTP/parser 用例为 `3 passed, 1 skipped`。这只改变重跑环境状态，
  不撤销已有本地 Chromium 证据；复现命令和证据路径见 Task 16 报告。

## ISOLATED_DEFERRED

- `python3 -m ruff check src tests scripts` 失败（exit 1），存在导入排序、未使用
  导入和其他既有 lint findings。
- 垂直切片定向检查为 8 passed、1 failed；失败用例收到 `DATA_UNAVAILABLE`，预期
  `LEARNING_RECORDED`。
- 并发运行时存在已复现的调度相关 fork 与 `multiprocessing.Queue` feeder-thread
  风险：子进程可能无法发布结果，最终表现为 `RESOURCE_LIMIT`。诊断记录在
  `runtime-concurrency-diagnosis.md`；修复和完整重跑尚未完成。
- Qlib/vectorbt/QMT 等可选边界保持隔离或只读，不能提升为默认权威引擎。

## EXTERNAL_UNVERIFIED

- 真实供应商、用户模型 endpoint、凭证授权、网络行为和生产部署均没有本次门禁所
  需的外部证据；生产浏览器/设备矩阵、真实网络浏览器行为和屏幕阅读器 conformance
  也仍未验证。
- mock provider、fixture 和离线 fallback 只证明合同与失败闭合，不证明外部服务
  可用性或供应商合规。

## NOT_IN_SCOPE

- 券商交易、实盘下单、真实资金、投资建议、秘密值进入 artifact、任意代码或 URL
  执行、无人值守自我改进均不属于本版本。

## 安全与研究完整性审查

报告、状态墙和前端合同继续要求 paper-only/read-only 语义、稳定 digest、PIT、
证据引用、人工准入和失败时不可决策。没有把外部连接或失败检查标为通过；没有
在本任务中推送、合并或声称生产发布。

## 复现命令

```bash
python3 -m compileall -q src tests
python3 scripts/validate_governance.py .
python3 -m pip check
python3 -m ruff check src tests scripts
cd frontend && npm test
```
