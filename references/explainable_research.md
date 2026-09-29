# Explainable Research Layer 与预测知识学习系统

v1.3.0 的解释层把一次研究运行组织成四类证据等级：

- `observed`：数据、质量、来源、时间点和监控 artifact 直接观察到的状态；
- `predictive`：模型、特征贡献、误差和区间说明的预测关系；
- `decision`：在约束、成本和风险目标下形成的组合或研究动作；
- `causal_hypothesis`：需要干预设计、识别假设和混杂控制，默认标记 `not_available`。

## 运行顺序

`analysis.json`、`rolling_evaluation.json`、`portfolio_robustness.json`、`monitoring_status.json`、source reconciliation 和 result lineage 先进入 `scripts/knowledge/explanation_engine.py`。随后依次生成 `knowledge_explanations.json`、`learning_cards.json`，读取 `knowledge/catalog.yaml` 和 `knowledge/concepts/`，编译 `formula_registry.py` 中的公式，保存 `formula_manifest.json`，最后交给离线 HTML renderer。MCP 只读取这些 artifact，不在客户端重新计算。

## 证据规则

每个 claim 必须带 `claim_id`、`claim_level`、`claim_type`、`formula_id`、`evidence_refs`、`calculation_refs`、`source_ids`、`input_hash`、`confidence`、`caveats` 和 `next_check`。若没有可匹配的计算 lineage，statement、confidence 和 status 必须为 `not_available`，而不能以固定文案补齐数值。

`scripts/knowledge/evidence_linker.py` 将 artifact 和 JSON pointer 绑定到 result-lineage 的 `calculation_id` 与 `input_hash`；`lesson_engine.py` 再把同一个 claim 变成概念、机制、公式、例子、限制和自测问题。

## 知识库边界

仓库只保存原创结构化摘要、公式、诊断规则和权威来源链接，不复制受版权保护的整本书或论文。知识卡片必须能回指来源，并且必须与本次运行的 evidence refs 分开：来源解释“概念如何定义”，lineage 解释“本次数值如何得到”。

## 公式状态

公式状态只能是 `not_attempted`、`compiling`、`compiled`、`blocked`、`failed` 或 `not_available`。没有 compiler 时使用 `FORMULA_COMPILE_FAILED`，TeX 编译成功但 SVG 转换失败时使用 `FORMULA_RENDER_FAILED`。未有真实编译资产时不得标记 `compiled`，HTML 必须显示可访问的 TeX/MathML 文本替代。

## 学习卡

`learning_cards.schema.json` 要求每张卡包含概念、公式、变量、推导步骤、只来自 artifact 的数值例子、适用条件、失败边界、自测问题、evidence refs 和 lineage refs。缺少事实时卡片仍可展示概念，但数值部分必须为 `not_available`。
