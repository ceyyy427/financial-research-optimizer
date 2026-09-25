# Financial Research Optimizer

一个面向金融统计、深度学习和组合优化的可审计 Codex Skill。读取金融数据后，它会按模块分析、形成条件预测，并强制生成精炼的离线 HTML 摘要和决策表。

## 适用场景

- 搜索公开股票、指数、基金、期货、利率、汇率、商品或宏观数据；
- 分析市场状态、资讯主题、波动率和风险暴露；
- 比较 OLS、岭回归、ARMA/GARCH、LSTM、CNN、Transformer、贝叶斯模型和图模型；
- 进行滚动预测、概率校准、压力测试和多轮模型比较；
- 在交易成本、换手率、流动性、杠杆和风险预算约束下做组合优化。
- 将数据质量、市场状态、统计结构、风险尾部、预测比较和决策情景分模块呈现；每个模块同时给出事实、解释、预测、置信度和下一次检查项。
- 生成单文件、无外部依赖的 HTML 可视化摘要，以及 CSV/Markdown 决策表。

## 输出理念

Skill 把结果拆成四层：

1. 数据事实：来源、时间、字段和质量；
2. 统计/深度模型：条件分布、预测和不确定性；
3. 决策层：组合目标、约束、成本和优化结果；
4. 审计层：滚动验证、稳定性、压力测试和失败边界。

“最佳模型”只表示在预先声明的样本外指标和风险约束下表现最好的候选，不表示保证未来收益。Skill 不会自动下单。

## 可视化预览

生成的 HTML 是一个精炼的研究摘要：顶部给出结论、预测值、区间和置信度；中部按模块呈现数据、风险与模型证据；底部给出决策表和复现信息。

![生成的 HTML 摘要预览](assets/html-preview.svg)

HTML 会把预测后的指标直接绘制成内嵌 SVG 图，包括实际值与模型均值、预测区间、风险指标和模型比较结果。这样打开单个 HTML 文件即可查看，不依赖 CDN 或外部前端服务。

![滚动预测与实际指标](assets/forecast-metrics.svg)

![模型比较指标](assets/model-metrics.svg)

![风险与尾部指标](assets/risk-metrics.svg)

## 标准流程

scope -> source discovery -> data audit -> feature/label build -> baselines -> deep challengers -> rolling validation -> calibration -> portfolio optimization -> stress test -> selection -> modular summary -> HTML + decision table

每个阶段都要保存可检查的中间结果，避免只输出一个无法追溯的预测数字。任何完成的数据分析都必须至少产出：`analysis.json`、精炼 HTML、决策表和数据/模型审计记录。

## 标准呈现

默认按以下结构输出：

- 研究合同；
- 数据来源与质量审计；
- 内容/市场状态摘要；
- 特征和标签公式；
- 模型卡和假设；
- 滚动预测与校准；
- 组合目标与约束；
- 多轮比较和选择规则；
- 情景分析；
- 局限性与复现信息。

![标准呈现教学流程](assets/workflow-tutorial.svg)

阅读顺序是：先确认数据事实，再看统计与深度模型，最后阅读情景预测和决策表。图表只展示已有的计算结果，不替代滚动评估、数学推导或数据溯源。

## HTML 与决策表

结构化分析完成后运行：

```bash
python scripts/generate_financial_html.py analysis.json --output-dir artifacts --decision-format both
```

HTML 默认包含：标题与 as-of 时间、核心结论、目标/概率/区间、模块状态卡、预测与风险指标图、情景预测、风险提示和决策表。它内嵌 CSS/SVG，可离线打开，不依赖 CDN，不展示没有来源或不确定性说明的数字；完成的预测运行不得省略指标图。

示例文件：[`examples/financial_research_brief.html`](examples/financial_research_brief.html)。

决策表至少包含：优先级、模块、当前判断、建议动作/仓位姿态、触发条件、依据、风险、有效期、下一次检查。表中的“动作”是研究与决策支持表达，不是自动下单指令。

## 目录

![目录结构教学图](assets/directory-map.svg)

- SKILL.md：主说明和路由规则；
- references/content_contract.md：内容呈现契约；
- references/workflow_blueprint.md：流程状态机和多轮选择规则；
- references/model_derivations.md：模型数学推导摘要；
- references/data_provenance.md：公开数据来源与溯源规范；
- references/rolling_evaluation.md：滚动评估与组合优化规范；
- references/html_output_contract.md：结构化分析 JSON、HTML 和决策表契约；
- scripts/validate_financial_dataset.py：CSV 数据质量审计脚本。
- scripts/generate_financial_html.py：从结构化分析 JSON 生成离线 HTML 与决策表。
- assets/：HTML 预览、预测指标、模型比较、流程教学和目录说明图片；
- examples/：示例分析 JSON、生成的 HTML 和决策表。

## 快速调用

$financial-research-optimizer

示例：

使用 $financial-research-optimizer 搜索公开数据，比较 ARMA-GARCH、LSTM 和 Transformer 对沪深300未来20个交易日波动率的预测，在最大回撤、换手率和交易成本约束下进行多轮模型选择。

![快速调用教学图](assets/quick-call-tutorial.svg)

快速调用时至少写清楚五件事：数据源、研究对象、预测目标、风险/成本约束、交付物。Skill 会据此生成模块总结、预测区间、指标图、HTML 和决策表。

## 免责声明

这是研究与决策支持工具，不是投资顾问、交易执行器或收益保证器。任何结论都必须结合数据更新时间、模型不确定性、市场制度变化和用户自己的风险承受能力。
