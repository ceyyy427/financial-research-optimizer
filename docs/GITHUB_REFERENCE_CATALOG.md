# Finathink GitHub 量化研究参考目录

更新时间：2026-10-05

这份目录记录本次为 Finathink 下载并审查的开源项目。外部仓库只用于阅读、比较和提取设计思想，不会被自动安装、自动执行或直接加入 Finathink 的生产运行时。Finathink 仍然坚持“用户提供数据，系统负责本地编排、校验、研究、回测、风控和 HTML 报告”的边界。

## 已下载位置

所有仓库都放在核心工作区之外：

`/Users/mac/.codex/references/finathink-github-20261005/`

每个仓库均为浅克隆，保留了本次审查时的提交快照。没有运行其安装脚本、Docker、Notebook、数据下载器或交易接口。

## 首批重点项目

| 优先级 | 项目 | 许可证 | 主要学习内容 | Finathink 的处理 |
| --- | --- | --- | --- | --- |
| P0 | [Microsoft Qlib](https://github.com/microsoft/qlib) | MIT | 数据集、特征表达、模型、回测、风险和 workflow 的分层；`qrun` 展示从数据集到训练、回测、评估的完整闭环 | 只提取接口和流程思想；不把 Qlib 数据格式或全套依赖引入核心 |
| P0 | [Microsoft RD-Agent](https://github.com/microsoft/RD-Agent) | MIT | 因子/模型交替提案、代码实现、实验反馈、失败恢复和循环控制；重点看 `rdagent/app/qlib_rd_loop` 与 `rdagent/scenarios/qlib` | 作为“学习分析师 + 因子研究循环”的设计参考；先改造成 Finathink 的受限 Plan/DAG |
| P0 | [Alphalens Reloaded](https://github.com/stefan-jansen/alphalens-reloaded) | Apache-2.0 | 因子清洗、未来收益对齐、分位数组合、IC、ICIR、换手、衰减和 tear sheet | 最适合提取为 Finathink 的因子验收指标与 HTML 报表组件 |
| P0 | [PyAnomaly](https://github.com/chulwoohan/pyanomaly) | MIT | 资产定价特征生成、200+ firm characteristics、1D/2D 排序、因子回归、横截面回归和交易成本 | 作为“预验证因子库”和研究方法参考；不能直接照搬 WRDS 数据获取部分 |
| P1 | [alpha-mining-system](https://github.com/aznikline/alpha-mining-system) | MIT | 表达式因子、时间序列算子、遗传编程、DeepAlpha、因子评估、数据适配器和报告流程 | 适合学习自然语言到表达式的中间层；必须重做表达式解析/沙箱，不能直接使用其 `eval` 路径 |
| P1 | [vectorbt](https://github.com/polakowo/vectorbt) | Apache-2.0 + Commons Clause | 向量化信号、组合、交易成本、参数扫描、绩效和回撤分析 | 只借鉴批量实验与指标组织；由于 Commons Clause，商业产品不直接依赖，先实现 Finathink 自有窄接口 |
| P1 | [TradingAgents](https://github.com/TauricResearch/TradingAgents) | Apache-2.0 | 基本面、新闻、情绪、技术分析师，研究经理、风险辩论、交易员、组合经理、图式路由和 HTML 报告 | 与用户提供的压缩包交叉学习；只保留研究协作和审计结构，去掉实时交易/经纪商边界 |
| P1 | [FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) | Apache-2.0（另有商标政策） | “模型推理、代码计算、代理编排、系统验证”的分工；研究报告、确定性计算、数据血缘和多代理工作流 | 借鉴报告工件、provenance、计算与叙述分离；不复制其品牌、外部 API 或部署脚本 |

## 推荐阅读顺序

1. 先读 Qlib 的数据、dataset、workflow、backtest、strategy 和 report 目录，理解量化研究的工程边界。
2. 再读 RD-Agent 的 `QuantRDLoop`、proposal、developer、experiment 和 feedback，理解“假设 → 实现 → 运行 → 反馈 → 下一轮”的自动研究循环。
3. 读 Alphalens 的 `utils.py`、`performance.py`、`tears.py`，把因子清洗、未来收益对齐、IC/换手/衰减指标固定下来。
4. 读 PyAnomaly 的 `characteristics.py`、`factors.py`、`analytics.py`、`portfolio.py`，整理预验证因子清单和横截面检验方法。
5. 读 alpha-mining-system 的 `operators.py`、`factor_engine.py`、`evaluator.py`，只吸收表达式 DSL 和遗传搜索的接口思想。
6. 最后读 TradingAgents/FinRobot 的 analyst、manager、risk、report 和 provenance 结构，把因子研究接入现有多代理研究层。

## Finathink 应该吸收的统一因子挖掘流程

外部项目的共同优点不是“让模型直接选股”，而是把研究过程拆成可验证的中间工件。Finathink 的目标流程应固定为：

`研究情景 → 研究简报 → 数据就绪审计 → 目标/标签定义 → 因子候选生成 → 表达式/代码静态检查 → 因子计算 → 样本内/样本外检验 → 稳健性与衰减 → 风险过滤 → 策略组合 → 回测 → 决策卡与 HTML 报告`

其中：

- 候选生成可由 Codex 的学习分析师提出自然语言假设，再转换成受限 factor DSL；不能直接执行模型生成的任意 Python。
- DSL 只允许注册算子、字段、窗口和明确的缺失值/异常值规则；每次运行保存表达式、版本、数据快照和算子清单。
- 验收至少包含 IC 均值/标准差/ICIR、分位数收益、长短组合、换手、交易成本、行业/规模中性化、时间衰减、滚动窗口和样本外验证。
- 因子只有在数据血缘完整、无未来信息泄漏、通过风险规则和最低稳健性门槛后，才可以进入因子库；失败候选进入拒绝原因和可复现日志。
- 组合和策略只生成研究信号与配置，不连接券商、不下单、不把外部数据源隐式接入用户环境。

## 外部项目的安全/复用边界

- 所有仓库都可能包含联网数据适配器、模型 API 调用、Docker 或可执行脚本；本次只做静态阅读，没有执行这些入口。
- alpha-mining-system 的因子表达式路径使用了受限 `eval`，这类模式不能进入 Finathink；需要 AST 白名单解释器。
- TradingAgents、FinRobot 和 vectorbt 依赖较多、部分功能面向外部 API 或交易/部署；它们只作为架构参考。
- Qlib、RD-Agent、FinRL 类项目覆盖面很大，不能把它们的所有依赖一次性装入核心环境；需要独立研究环境或适配器。
- PyAnomaly 的数据部分面向 WRDS 等受许可数据源；Finathink 不替用户下载或转发受限数据。
- 外部许可证允许学习并不等于允许复制品牌、数据、模型权重或第三方服务；分发前仍需保留许可证和 NOTICE，并单独做依赖许可证审查。

## 下一步实现建议

第一阶段只实现 Finathink 自己的窄接口：`FactorCandidate`、`FactorExpression`、`FactorEvaluation`、`FactorDecayProfile`、`FactorAdmissionDecision` 和 `StrategyResearchArtifact`。用内置离线样例数据跑通 Alphalens/PyAnomaly 启发的检验指标和 HTML 报告，不安装外部仓库。

第二阶段实现受限 factor DSL 和算子注册表，接入 Codex 学习分析师的“假设—候选—修正”循环；每一轮只能提交结构化提案，必须通过静态检查和确定性计算。

第三阶段再增加可选的 Qlib/RD-Agent 适配实验，适配器放到独立的 `research_adapters/`，默认关闭，并在报告中标注外部依赖、版本和许可证。

第四阶段把 TradingAgents/FinRobot 的角色协作接入研究情景层：基本面、技术、情绪、新闻、学习分析师 → 研究经理 → 风险经理 → 组合经理 → 报告器；所有代理输出都只能产生可审计工件，不能绕过风控直接执行。

## 本次快照

| 项目 | 提交 |
| --- | --- |
| Qlib | `be725493eb1a6bbb42bf11b37aa7669f59610ff1` |
| RD-Agent | `484776c211e4fbbeef03e0ec00d6bbee7362a4f4` |
| Alphalens Reloaded | `f0a07c22d554e4b4036983cc80320b432714fe7e` |
| vectorbt | `ceffc501f2d37033a79dd86a9f883e69ec6977bd` |
| PyAnomaly | `59758c913a4146bbfb9d3c056668ccdc5231c8c8` |
| TradingAgents | `1394a3f72aa4393e1a98f51b382434c4b4c2d972` |
| FinRobot | `2717499b8e30f242640af08c4ad9afd1113c2d45` |
| alpha-mining-system | `7b149c298e01dc6f45f87db0b8d55ced89c979ea` |

