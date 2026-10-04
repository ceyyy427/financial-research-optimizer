"""Content and code quality gates for canonical P8.2B units."""

from __future__ import annotations

import ast
import math

from .contracts import KnowledgeUnit

_BANNED_NAMES = {"eval", "exec", "open", "compile", "__import__", "input"}
_BANNED_MODULES = {"os", "sys", "subprocess", "socket", "requests", "httpx", "pathlib", "shutil"}


def validate_code(source: str) -> None:
    if not isinstance(source, str) or not source.strip():
        raise ValueError("code is required")
    try:
        tree = ast.parse(source, mode="exec")
    except SyntaxError as exc:
        raise ValueError("code syntax is invalid") from exc
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = node.names[0].name.split(".", 1)[0]
            raise ValueError(f"unsafe import: {module}")  # noqa: TRY004 - caller receives one validation error type
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _BANNED_NAMES:
            raise ValueError(f"unsafe call: {node.func.id}")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise ValueError("unsafe attribute")
        if isinstance(node, ast.Name) and node.id in _BANNED_MODULES:
            raise ValueError(f"unsafe module: {node.id}")


def _symbols(expression: dict[str, object]) -> set[str]:
    if expression["type"] == "symbol":
        return {str(expression["name"])}
    if expression["type"] in {"number"}:
        return set()
    if expression["type"] == "unary":
        return _symbols(expression["value"])
    if expression["type"] == "binary":
        return _symbols(expression["left"]) | _symbols(expression["right"])
    return set().union(*(_symbols(arg) for arg in expression["args"]))


def _acyclic(units: dict[str, KnowledgeUnit]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(unit_id: str) -> None:
        if unit_id in visiting:
            raise ValueError("prerequisite cycle")
        if unit_id in visited:
            return
        visiting.add(unit_id)
        for prerequisite in units[unit_id].prerequisites:
            if prerequisite not in units:
                raise ValueError(f"unknown prerequisite: {prerequisite}")
            visit(prerequisite)
        visiting.remove(unit_id)
        visited.add(unit_id)

    for unit_id in units:
        visit(unit_id)


def validate_catalog(catalog: object) -> tuple[str, ...]:
    units = tuple(catalog.units)
    by_id = {unit.unit_id: unit for unit in units}
    if len(by_id) != len(units):
        raise ValueError("duplicate unit_id")
    _acyclic(by_id)
    references = {record.reference_id for record in catalog.references.records()}
    for unit in units:
        if not unit.why_now or not unit.provenance:
            raise ValueError(f"{unit.unit_id} lacks provenance or why_now")
        symbol_ids = {symbol.symbol_id for symbol in unit.symbols}
        equation_ids = {equation.equation_id for equation in unit.equations}
        for equation in unit.equations:
            if not _symbols(equation.expression.node) <= symbol_ids:
                raise ValueError(f"{unit.unit_id} equation has unknown symbol")
        for derivation in unit.derivations:
            if derivation.previous_equation_id and derivation.previous_equation_id not in equation_ids:
                raise ValueError(f"{unit.unit_id} derivation has unknown equation")
        step_ids = {step.step_id for step in unit.derivations}
        for proof in unit.proofs:
            if not set(proof.step_ids) <= step_ids:
                raise ValueError(f"{unit.unit_id} proof has unknown step")
        if not set(unit.references) <= references:
            raise ValueError(f"{unit.unit_id} cites unknown reference")
        for segment in unit.code_segments:
            validate_code(segment.code)
            if not set(segment.equation_ids) <= equation_ids:
                raise ValueError(f"{unit.unit_id} code has unknown equation")
        for symbol in unit.symbols:
            if symbol.current_value is not None and not math.isfinite(float(symbol.current_value)):
                raise ValueError(f"{unit.unit_id} symbol is non-finite")
    return tuple(sorted(by_id))
