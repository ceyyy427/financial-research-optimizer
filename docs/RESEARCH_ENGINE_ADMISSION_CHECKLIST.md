# 研究引擎准入清单

本清单用于可选 Qlib/vectorbt 适配器的隔离审查。它不审查用户选择的
数据供应商，也不要求平台购买数据或保存用户 API Key。

## 必须全部通过的门禁

- **软件版本**：固定版本和运行时版本已记录；核心环境不因适配器而改变。
- **许可证**：上游许可证、可选 extras 和发布/托管限制已记录；未审查不标记
  `AVAILABLE`。
- **隔离环境**：必须由部署方提供并审计一个外部 OS/container sandbox runner。
  Python 进程内 monkeypatch（包括本地 `RestrictedProcessRunner`）不能证明隔离，
  因此当前核心默认不提供 `AVAILABLE` 引擎。仅设置 `isolated=true` 或
  `controlled_runner=true` 不算通过，不提供可验证 runner 时状态必须是
  `DEFERRED`。适配器不执行用户提供的 Python、Shell、SQL 或动态模块。
- **归一数据 fixture**：输入只能是 Finathink `DatasetSnapshot` 或同等已通过
  合同校验的离线 fixture；适配器不能发现、下载或替换行情数据。
- **结果边界**：输出只能是 `MLResearchResult` 或 `SweepResult`；第三方数据集、
  模型、Portfolio、handler 和原始对象不得进入 artifact、日志或浏览器。
- **回退路径**：缺少依赖、门禁不完整、超时或适配器错误时，必须回到确定性的
  Finathink 引擎，并在结果中记录实际引擎与 `fallback_reason`。

## 状态含义

| 状态 | 含义 |
| --- | --- |
| `AVAILABLE` | 仅在外部 OS/container sandbox runner 可验证、且六项门禁全部通过时允许；当前核心默认无此状态。 |
| `NOT_INSTALLED` | 可选依赖不在批准的隔离环境中；使用 Finathink 回退。 |
| `DEFERRED` | 已有环境或适配器，但至少一项门禁缺失；不得执行外部引擎。 |

## 最小验证步骤

1. 在一次性隔离环境记录版本、许可证和 `pip check` 结果。
2. 用离线、已归一的 fixture 完成最小 ML 或 sweep smoke，不访问网络。
3. 序列化结果并扫描第三方类型、绝对路径、endpoint、凭证和原始对象。
4. 删除/隐藏可选依赖后重跑核心测试，确认离线回退和默认启动不变。
5. 运行 `EngineRegistry` 的回退、指纹、输入类型和错误边界测试。

任何一步未完成，registry 只能返回 `NOT_INSTALLED` 或 `DEFERRED`。通过状态不
代表数据源已核验、PIT 已补齐、策略有效或可以连接券商；Finathink 始终保持
paper-only。
