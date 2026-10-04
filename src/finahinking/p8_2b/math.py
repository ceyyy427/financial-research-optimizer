"""Small, safe mathematical expression AST used by the education layer."""

from __future__ import annotations

import html
import importlib.util
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from numbers import Real

_BINARY = {"+", "-", "*", "/", "^"}
_FUNCTIONS = {"abs", "exp", "log", "sqrt", "mean", "std", "partition"}


def _finite(value: float) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("number must be finite")
    return number


def _node(value: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError("AST node must be an object")
    kind = value.get("type")
    if kind == "symbol":
        name = value.get("name")
        if not isinstance(name, str) or not name or any(char.isspace() for char in name):
            raise ValueError("symbol name is invalid")
        return {"type": "symbol", "name": name}
    if kind == "number":
        raw = value.get("value")
        if not isinstance(raw, Real):
            raise ValueError("number value is invalid")
        return {"type": "number", "value": _finite(float(raw))}
    if kind == "unary":
        if value.get("op") != "neg":
            raise ValueError("unary operation is invalid")
        return {"type": "unary", "op": "neg", "value": _node(value.get("value", {}))}
    if kind == "binary":
        op = value.get("op")
        if op not in _BINARY:
            raise ValueError("binary operation is invalid")
        return {"type": "binary", "op": op, "left": _node(value.get("left", {})), "right": _node(value.get("right", {}))}
    if kind == "function":
        name = value.get("name")
        args = value.get("args")
        if name not in _FUNCTIONS or not isinstance(args, list) or not args or len(args) > 4:
            raise ValueError("function node is invalid")
        return {"type": "function", "name": name, "args": [_node(item) for item in args]}
    raise ValueError("AST node type is invalid")


def _canonical(node: Mapping[str, object]) -> str:
    return json.dumps(_node(node), sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class MathExpression:
    """Canonical expression storage; renderings are derived on demand."""

    ast: str

    def __post_init__(self) -> None:
        try:
            canonical = _canonical(json.loads(self.ast))
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("ast must be canonical JSON") from exc
        object.__setattr__(self, "ast", canonical)

    @classmethod
    def from_node(cls, node: Mapping[str, object]) -> MathExpression:
        return cls(_canonical(node))

    @classmethod
    def symbol(cls, name: str) -> MathExpression:
        return cls.from_node({"type": "symbol", "name": name})

    @classmethod
    def number(cls, value: Real) -> MathExpression:
        return cls.from_node({"type": "number", "value": _finite(float(value))})

    @classmethod
    def negate(cls, value: MathExpression) -> MathExpression:
        return cls.from_node({"type": "unary", "op": "neg", "value": value.node})

    @classmethod
    def binary(cls, op: str, left: MathExpression, right: MathExpression) -> MathExpression:
        if op not in _BINARY:
            raise ValueError("binary operation is invalid")
        return cls.from_node({"type": "binary", "op": op, "left": left.node, "right": right.node})

    @classmethod
    def add(cls, left: MathExpression, right: MathExpression) -> MathExpression:
        return cls.binary("+", left, right)

    @classmethod
    def subtract(cls, left: MathExpression, right: MathExpression) -> MathExpression:
        return cls.binary("-", left, right)

    @classmethod
    def multiply(cls, left: MathExpression, right: MathExpression) -> MathExpression:
        return cls.binary("*", left, right)

    @classmethod
    def divide(cls, left: MathExpression, right: MathExpression) -> MathExpression:
        return cls.binary("/", left, right)

    @classmethod
    def power(cls, left: MathExpression, right: MathExpression) -> MathExpression:
        return cls.binary("^", left, right)

    @classmethod
    def function(cls, name: str, *args: MathExpression) -> MathExpression:
        return cls.from_node({"type": "function", "name": name, "args": [arg.node for arg in args]})

    @property
    def node(self) -> dict[str, object]:
        return json.loads(self.ast)

    @property
    def fingerprint(self) -> str:
        return sha256(self.ast.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {"ast": self.node, "fingerprint": self.fingerprint}


def _precedence(node: Mapping[str, object]) -> int:
    if node["type"] == "binary":
        return {"+": 10, "-": 10, "*": 20, "/": 20, "^": 30}[str(node["op"])]
    if node["type"] == "unary":
        return 25
    return 40


def _latex(node: Mapping[str, object], parent_precedence: int = 0, *, right_child: bool = False) -> str:
    kind = node["type"]
    if kind == "symbol":
        return str(node["name"])
    if kind == "number":
        return format(float(node["value"]), ".15g")
    if kind == "unary":
        value = _latex(node["value"], _precedence(node))
        if _precedence(node["value"]) < _precedence(node):
            value = rf"\left({_latex(node['value'])}\right)"
        return "-" + value
    if kind == "binary":
        op = str(node["op"])
        precedence = _precedence(node)
        left = _latex(node["left"], precedence)
        right = _latex(node["right"], precedence, right_child=True)
        if op == "/":
            rendered = rf"\frac{{{_latex(node['left'])}}}{{{_latex(node['right'])}}}"
        elif op == "^":
            rendered = rf"{{{_latex(node['left'])}}}^{{{_latex(node['right'])}}}"
        elif op == "*":
            rendered = f"{left} \\cdot {right}"
        else:
            rendered = f"{left} {op} {right}"
        if precedence < parent_precedence or (right_child and op in {"-", "/"} and precedence == parent_precedence):
            return rf"\left({rendered}\right)"
        return rendered
    name = str(node["name"])
    args = node["args"]
    if name == "partition":
        if len(args) == 2:
            return f"{_latex(args[0])} \\sqcup {_latex(args[1])}"
        return f"{_latex(args[0])} = {_latex(args[1])} \\sqcup {_latex(args[2])}"
    if name == "sqrt":
        return rf"\sqrt{{{_latex(args[0])}}}"
    command = {"abs": "left|", "exp": "exp", "log": "log", "mean": "operatorname{mean}", "std": "operatorname{std}"}[name]
    if name == "abs":
        return rf"\left|{_latex(args[0])}\right|"
    return rf"\{command}\left({_latex(args[0])}\right)"


def render_latex(expression: MathExpression) -> str:
    return _latex(expression.node)


def _mathml(node: Mapping[str, object]) -> str:
    kind = node["type"]
    if kind == "symbol":
        return f"<mi>{html.escape(str(node['name']))}</mi>"
    if kind == "number":
        return f"<mn>{html.escape(format(float(node['value']), '.15g'))}</mn>"
    if kind == "unary":
        return f"<mrow><mo>−</mo>{_mathml(node['value'])}</mrow>"
    if kind == "binary":
        op = str(node["op"])
        if op == "/":
            return f"<mfrac>{_mathml(node['left'])}{_mathml(node['right'])}</mfrac>"
        if op == "^":
            return f"<msup>{_mathml(node['left'])}{_mathml(node['right'])}</msup>"
        return f"<mrow>{_mathml(node['left'])}<mo>{html.escape(op)}</mo>{_mathml(node['right'])}</mrow>"
    name = html.escape(str(node["name"]))
    args = "".join(_mathml(arg) for arg in node["args"])
    if name == "partition" and len(node["args"]) == 2:
        return f"<mrow>{_mathml(node['args'][0])}<mo>⊔</mo>{_mathml(node['args'][1])}</mrow>"
    if name == "partition" and len(node["args"]) == 3:
        return f"<mrow>{_mathml(node['args'][0])}<mo>=</mo>{_mathml(node['args'][1])}<mo>⊔</mo>{_mathml(node['args'][2])}</mrow>"
    return f"<mrow><mi>{name}</mi><mo>⁡</mo><mfenced>{args}</mfenced></mrow>"


def render_mathml(expression: MathExpression) -> str:
    return f'<math xmlns="http://www.w3.org/1998/Math/MathML" display="block">{_mathml(expression.node)}</math>'


def _evaluate(node: Mapping[str, object]) -> float:
    kind = node["type"]
    if kind == "number":
        return float(node["value"])
    if kind == "unary":
        return -_evaluate(node["value"])
    if kind == "binary":
        left, right = _evaluate(node["left"]), _evaluate(node["right"])
        op = node["op"]
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            if right == 0:
                raise ValueError("division by zero")
            return left / right
        return left**right
    name = str(node["name"])
    values = [_evaluate(arg) for arg in node["args"]]
    if name == "abs":
        return abs(values[0])
    if name == "exp":
        return math.exp(values[0])
    if name == "log":
        return math.log(values[0])
    if name == "sqrt":
        return math.sqrt(values[0])
    if name == "mean":
        return sum(values) / len(values)
    if name == "std":
        mean = sum(values) / len(values)
        return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))
    if name == "partition":
        raise ValueError("partition is structural and cannot be numerically evaluated")
    raise ValueError("unsupported function")


def evaluate(expression: MathExpression) -> float:
    value = _evaluate(expression.node)
    return _finite(value)


def _substitute(node: Mapping[str, object], values: Mapping[str, Real]) -> dict[str, object]:
    if node["type"] == "symbol":
        name = str(node["name"])
        if name not in values:
            raise ValueError(f"unknown symbol: {name}")
        return {"type": "number", "value": _finite(float(values[name]))}
    if node["type"] in {"number"}:
        return dict(node)
    if node["type"] == "unary":
        return {"type": "unary", "op": "neg", "value": _substitute(node["value"], values)}
    if node["type"] == "binary":
        return {"type": "binary", "op": node["op"], "left": _substitute(node["left"], values), "right": _substitute(node["right"], values)}
    return {"type": "function", "name": node["name"], "args": [_substitute(arg, values) for arg in node["args"]]}


def substitute(expression: MathExpression, values: Mapping[str, Real]) -> MathExpression:
    return MathExpression.from_node(_substitute(expression.node, values))


def _normal(node: Mapping[str, object]) -> object:
    kind = node["type"]
    if kind == "binary" and node["op"] in {"+", "*"}:
        children = sorted((_normal(node["left"]), _normal(node["right"])), key=repr)
        return ("binary", node["op"], *children)
    if kind == "binary":
        return ("binary", node["op"], _normal(node["left"]), _normal(node["right"]))
    if kind == "unary":
        return ("unary", _normal(node["value"]))
    if kind == "function":
        return ("function", node["name"], tuple(_normal(arg) for arg in node["args"]))
    return tuple(sorted(node.items()))


def equivalent(left: MathExpression, right: MathExpression) -> bool:
    return _normal(left.node) == _normal(right.node)


def symbolic_equivalence(left: MathExpression, right: MathExpression) -> tuple[bool, str]:
    """Use SymPy only when installed; return an explicit verification label."""

    if importlib.util.find_spec("sympy") is None:
        return equivalent(left, right), "UNAVAILABLE_AST_NORMALIZATION"
    try:
        import sympy as sp  # type: ignore[import-not-found]

        def convert(node: Mapping[str, object]) -> object:
            kind = node["type"]
            if kind == "symbol":
                return sp.Symbol(str(node["name"]))
            if kind == "number":
                return sp.Float(float(node["value"]))
            if kind == "unary":
                return -convert(node["value"])
            if kind == "binary":
                left_value, right_value = convert(node["left"]), convert(node["right"])
                return {"+": lambda: left_value + right_value, "-": lambda: left_value - right_value, "*": lambda: left_value * right_value, "/": lambda: left_value / right_value, "^": lambda: left_value**right_value}[node["op"]]()
            args = [convert(arg) for arg in node["args"]]
            return {"abs": sp.Abs, "exp": sp.exp, "log": sp.log, "sqrt": sp.sqrt, "mean": lambda *values: sum(values) / len(values), "std": lambda *values: sp.sqrt(sum((value - sum(values) / len(values)) ** 2 for value in values) / (len(values) - 1))}[node["name"]](*args)

        return bool(sp.simplify(convert(left.node) - convert(right.node)) == 0), "SYMBOLICALLY_VERIFIED"
    except Exception:  # noqa: BLE001 - optional adapter must fail closed with a label
        return equivalent(left, right), "AST_FALLBACK"
