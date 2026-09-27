# Result lineage contract

`analysis.json` is not evidence merely because it validates as JSON. Every numerical value that enters the HTML or decision table must point to a verified result-lineage record.

Each record declares:

```json
{
  "metric_id": "forecast_rmse",
  "value": 0.023,
  "calculation_id": "calc_20260926_001",
  "input_hash": "sha256:…",
  "code_version": "financial-research-optimizer@961cee1",
  "formula": "sqrt(mean((y-yhat)^2))",
  "source_ids": ["price_source_1"]
}
```

`verify_result_lineage.py` checks required fields, unique IDs, optional raw-input hashes, calculation fingerprints, chart series, sparkline series, module metrics, and numerical audit blocks. A chart or audit block must include `lineage_refs` that resolve to `metric_id` values. A top-level `series` must include `series_lineage_refs`.

The HTML generator invokes the same verifier before writing any artifact. Missing `source_ids`, `calculation_id`, `input_hash`, `code_version`, or `formula` is a blocking error. The verifier is intentionally conservative: narrative strings and metadata such as dates, seeds, and row counts are not treated as calculated metrics, while native numerical arrays used in figures are.

可复算指标还应记录 `recompute_command`、`output_file`、`output_hash`、
`dependency_versions` 和 `dependency_lock_hash`。`--recompute` 模式会执行无 shell
命令、检查退出码，并在声明输出文件时重新计算 SHA-256；缺少复算命令或输出哈希
会阻止“可复算”状态，但不会把普通演示数据误报成可复算。

For an online run, `input_hash` should be the hash of the immutable snapshot saved by `snapshot_store.py`, and `source_ids` should reference the provenance manifest. For a model run, `calculation_id` should be stable across the HTML, decision table, model card, and experiment manifest.

Run:

```bash
python3 scripts/verify_result_lineage.py examples/demo_analysis.json
```

Do not hand-edit a metric value after calculation. Recompute the value, update its input/code fingerprints, and regenerate the HTML and decision table.
