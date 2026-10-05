# Finathink 流程图与视觉规范

这套规范用于 Finathink 的 README、研究指南、离线 HTML 报告和后续模块文档。它吸收了 Qlib 的分层研究管线、RD-Agent 的实验循环、TradingAgents 的阶段状态墙，以及 FinRobot 的报告工件组织方式，再用 Finathink 自己的事件、知识、因子、风控和学习语言重新表达。

## 视觉目标

- 让读者先看到研究链路，再进入代码和契约细节。
- 让每个模块拥有稳定颜色、图标和动作语义。
- 让“数据从哪里来、经过哪些检查、产生什么工件”一眼可读。
- 让图表在 GitHub、Markdown 阅读器和离线 HTML 中都能独立显示。
- 让颜色之外仍保留中文文字、箭头方向和可访问的 `alt`/`title` 描述。

## 模块颜色

颜色只表示模块语义，不表示结果好坏。所有 SVG 都在图中内嵌颜色，因此可以脱离网站独立打开。

| Token | 颜色 | 模块 | 图标语义 |
| --- | --- | --- | --- |
| `--module-event` | `#2563EB` | 事件 | 时间点、发布、观察 |
| `--module-evidence` | `#0891B2` | 证据 | 来源、引用、核验 |
| `--module-knowledge` | `#7C3AED` | 知识 | 书本、方程、解释 |
| `--module-data` | `#15803D` | 数据 | 快照、表格、血缘 |
| `--module-quant` | `#D97706` | 量化 | 曲线、统计、实验 |
| `--module-factor` | `#EA580C` | 因子 | 算子、特征、排序 |
| `--module-risk` | `#DC2626` | 风控 | 护盾、门禁、状态 |
| `--module-report` | `#334155` | 报告与学习 | 文档、归档、下一问 |

## 图形规则

### 节点

- 每个节点使用圆角卡片：模块色用于左侧色条、图标圆和状态徽章。
- 节点标题使用中文，英文只保留代码名、API 路径或协议名。
- 每个节点最多放一行动作说明；更长内容放在对应指南中。
- 小图案使用原创线性 SVG 图标：圆、线、折线、书页、盾牌、文档和数据堆。

### 箭头

- 实线箭头表示数据或研究工件的正常流转。
- 虚线箭头表示解释、学习或回到下一轮问题的反馈。
- 箭头必须有方向；并行分析使用分叉后再汇合的结构。
- 风控门禁使用红色状态节点，但不把颜色作为唯一含义。

### 状态

- `输入`：白底、模块色边框。
- `处理中`：模块色填充、浅色文字。
- `产出`：深色报告色填充、白色文字。
- `反馈`：虚线回路，配合“下一轮研究问题”文字。

### 可访问性

- 每个 SVG 必须含有 `<title>`、`<desc>`、`role="img"` 和 `viewBox`。
- Markdown 图片必须写中文 `alt` 文本。
- 颜色对比度以文字可读为准；需要表达状态时同时写出中文标签。
- 图表不能承载唯一信息，正文必须保留同一条流程的文字版本。

## 图集

| 图 | 用途 |
| --- | --- |
| [`finathink-overview.svg`](diagrams/finathink-overview.svg) | 从事件到报告与学习的总流程 |
| [`event-evidence.svg`](diagrams/event-evidence.svg) | 事件、来源、主张、证据和学习 |
| [`knowledge-path.svg`](diagrams/knowledge-path.svg) | 直觉到公式、代码和应用 |
| [`quant-research.svg`](diagrams/quant-research.svg) | 量化问题、数据审计、实验和验证 |
| [`factor-workbench.svg`](diagrams/factor-workbench.svg) | 数据、因子 DSL、信号、仓位和台账 |
| [`strategy-risk.svg`](diagrams/strategy-risk.svg) | 策略想法、回测、OOS、风控和决策卡 |
| [`research-agents.svg`](diagrams/research-agents.svg) | 多角色分析、研究经理、工具和报告 |
| [`report-learning.svg`](diagrams/report-learning.svg) | 证据、结果、HTML 报告、工作区和下一问 |

## 嵌入规则

README 使用总图和图集入口；专题指南在对应章节放一张模块图；HTML 报告可以继续使用同样的颜色语义绘制内联 SVG。新增模块时，先补充颜色 token、图标语义和图集索引，再添加模块图和正文说明。
