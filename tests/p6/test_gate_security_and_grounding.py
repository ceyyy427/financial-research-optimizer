import ast
from pathlib import Path

import pytest

from finahinking.p6.gateway import P6QuantGateway
from finahinking.p6.models import TypedToolRequest
from finahinking.p6.security import validate_payload

ROOT = Path(__file__).resolve().parents[2]


def test_typed_tool_request_rejects_mutation_and_import_payloads() -> None:
    for payload in ({"import": "os"}, {"source_code": "print(1)"}, {"delete_artifact": True}, {"eval": "x"}):
        with pytest.raises(ValueError):
            TypedToolRequest("quant.run_backtest", payload)
        with pytest.raises(ValueError):
            validate_payload(payload)


def test_p6_gateway_rejects_unapproved_tool_names() -> None:
    response = P6QuantGateway().execute(TypedToolRequest("quant.optimize_portfolio", {}))
    assert response.status == "REJECTED"


def test_p6_source_has_no_dynamic_execution_or_optional_direct_imports() -> None:
    for path in (ROOT / "src/finahinking/p6").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"eval", "exec", "compile"}
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [alias.name for alias in node.names]
                assert not any(name.split(".")[0] in {"statsmodels", "vectorbt", "qlib", "langgraph"} for name in names)
