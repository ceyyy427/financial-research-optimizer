"""Path-safe export of a bounded P6.6 research/education package."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from finahinking.experiments.models import canonical_json

from .education import generate_educational_code, scan_educational_code

_MAX_FILE_BYTES = 1_000_000
_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,96}$")
_SECRET_KEY = re.compile(r"(secret|credential|password|token|api[_-]?key|private[_-]?key)", re.IGNORECASE)
_SECRET_VALUE = re.compile(r"(AKIA[0-9A-Z]{12,}|-----BEGIN .*PRIVATE KEY-----|Bearer\s+[A-Za-z0-9._-]{12,})", re.IGNORECASE)


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_safe(v) for v in value]
    if hasattr(value, "to_dict"):
        return _safe(value.to_dict())
    if hasattr(value, "item"):
        try:
            return _safe(value.item())
        except (TypeError, ValueError):
            return None
    return value


def _assert_no_secrets(value: Any, path: str = "payload") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            if _SECRET_KEY.search(key_text):
                raise ValueError(f"export contains sensitive field: {path}.{key_text}")
            _assert_no_secrets(item, f"{path}.{key_text}")
    elif isinstance(value, (list, tuple, set)):
        for index, item in enumerate(value):
            _assert_no_secrets(item, f"{path}[{index}]")
    elif isinstance(value, str) and _SECRET_VALUE.search(value):
        raise ValueError(f"export contains a credential-like value at {path}")


def _json_text(value: Any) -> str:
    normalized = _safe(value)
    _assert_no_secrets(normalized)
    return json.dumps(normalized, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def _safe_relative(name: str) -> Path:
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ValueError("export path must be relative")
    path = Path(name)
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("export path traversal is not allowed")
    return path


@dataclass(frozen=True)
class ResearchPackage:
    root: str
    files: tuple[str, ...]
    package_fingerprint: str
    educational_scan: Mapping[str, Any]
    provenance: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"root": self.root, "files": list(self.files), "package_fingerprint": self.package_fingerprint, "educational_scan": dict(self.educational_scan), "provenance": dict(self.provenance)}


class ResearchPackageExporter:
    """Write only the fixed, non-deployment P6.6 research artifact layout."""

    required_files = ("strategy.py", "features.py", "config.json", "strategy_spec.json", "math_notes.md", "strategy_logic.md", "research_report.json", "limitations.md", "provenance.json", "README.md", "tests/test_package.py")

    def export(self, destination: str | os.PathLike[str], *, strategy_spec: Any, feature_graph: Any = None, config: Any = None, research_report: Any = None, provenance: Any = None, educational_code: str | None = None, features_code: str | None = None, math_notes: str | None = None, strategy_logic: str | None = None, limitations: str | None = None, package_name: str = "research_package") -> ResearchPackage:
        if not _SAFE_NAME.fullmatch(package_name):
            raise ValueError("package_name is invalid")
        root = Path(destination).expanduser().resolve() / package_name
        root.mkdir(parents=True, exist_ok=True)
        strategy_payload = _safe(strategy_spec)
        graph_payload = _safe(feature_graph if feature_graph is not None else {})
        config_payload = _safe(config if config is not None else {})
        report_payload = _safe(research_report if research_report is not None else {})
        provenance_payload = _safe(provenance if provenance is not None else {})
        for payload in (strategy_payload, graph_payload, config_payload, report_payload, provenance_payload):
            _assert_no_secrets(payload)
        if educational_code is not None:
            code = educational_code
        else:
            # The educational generator requires a reviewed StrategySpec and
            # compiled IR.  Export also accepts a serialized/spec mapping, so
            # use a comment-only fallback in that case; it is intentionally not
            # executable and remains covered by the same AST scan.
            try:
                from .compiler import strategy_ir
                from .models import StrategySpec

                if isinstance(strategy_spec, StrategySpec):
                    code = generate_educational_code(strategy_spec, strategy_ir(strategy_spec)).source
                else:
                    strategy_name = strategy_payload.get("strategy_id", strategy_payload.get("name", "reviewed_strategy")) if isinstance(strategy_payload, Mapping) else "reviewed_strategy"
                    code = "# EDUCATIONAL ARTIFACT — never auto-execute; research/teaching only.\n" + f"# Strategy: {strategy_name}\n# The validated Strategy IR is the execution representation.\n"
            except (TypeError, ValueError, AttributeError):
                code = "# EDUCATIONAL ARTIFACT — never auto-execute; research/teaching only.\n# The validated Strategy IR is the execution representation.\n"
        scan = scan_educational_code(code)
        scan_safe = bool(getattr(scan, "safe", scan.get("safe") if isinstance(scan, Mapping) else False))
        scan_violations = getattr(scan, "violations", scan.get("violations", ()) if isinstance(scan, Mapping) else ())
        scan_fingerprint = getattr(scan, "source_fingerprint", scan.get("source_fingerprint") if isinstance(scan, Mapping) else None)
        if not scan_safe:
            raise ValueError(f"educational code failed static safety scan: {scan_violations}")
        feature_text = features_code or "# EDUCATIONAL FEATURE LINEAGE — data-only description; never auto-execute.\n# Feature definitions are governed by the reviewed FeatureGraph.\n"
        feature_scan = scan_educational_code(feature_text)
        feature_safe = bool(getattr(feature_scan, "safe", feature_scan.get("safe") if isinstance(feature_scan, Mapping) else False))
        if not feature_safe:
            raise ValueError("feature artifact failed static safety scan")
        docs = {
            "strategy.py": code,
            "features.py": feature_text,
            "config.json": _json_text(config_payload),
            "strategy_spec.json": _json_text(strategy_payload),
            "math_notes.md": math_notes or "# Math notes\n\nThis package explains the reviewed strategy and reports historical evidence only.\n",
            "strategy_logic.md": strategy_logic or "# Strategy logic\n\nThe Strategy IR is the only execution representation. This file is explanatory.\n",
            "research_report.json": _json_text(report_payload),
            "limitations.md": limitations or "# Limitations\n\nResearch and paper replay are not investment advice, deployment, or real-money trading.\n",
            "README.md": "# Finahinking P6.6 research package\n\nThis is a bounded educational artifact. Reproduce with approved data, the recorded configuration, and the existing P5 engine. Do not deploy or connect it to a broker.\n",
            "tests/test_package.py": "\"\"\"Deterministic package smoke checks.\"\"\"\nfrom pathlib import Path\n\n\ndef test_package_is_educational() -> None:\n    assert 'broker' in Path(__file__).parents[1].joinpath('README.md').read_text().lower()\n",
        }
        for text in (docs["math_notes.md"], docs["strategy_logic.md"], docs["limitations.md"], docs["README.md"]):
            _assert_no_secrets(text)
        manifest: dict[str, str] = {}
        for name, text in docs.items():
            relative = _safe_relative(name)
            if not isinstance(text, str):
                raise TypeError(f"{name} must be text")
            encoded = text.encode("utf-8")
            if len(encoded) > _MAX_FILE_BYTES:
                raise ValueError(f"{name} exceeds export size limit")
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(encoded)
            manifest[name] = hashlib.sha256(encoded).hexdigest()
        provenance_envelope = {"schema_version": 1, "package_type": "research_education_only", "strategy_fingerprint": strategy_payload.get("fingerprint") if isinstance(strategy_payload, Mapping) else None, "feature_graph_fingerprint": graph_payload.get("fingerprint") if isinstance(graph_payload, Mapping) else None, "educational_source_fingerprint": scan_fingerprint, "files": dict(sorted(manifest.items())), "user_provenance": provenance_payload, "limitations": ["historical evidence only", "paper simulation only", "not broker-connected", "no automatic execution"]}
        provenance_envelope["package_fingerprint"] = _digest(provenance_envelope)
        provenance_text = _json_text(provenance_envelope)
        (root / "provenance.json").write_text(provenance_text, encoding="utf-8")
        manifest["provenance.json"] = hashlib.sha256(provenance_text.encode("utf-8")).hexdigest()
        package_fingerprint = _digest(manifest)
        # The provenance envelope records the authoritative pre-envelope manifest
        # fingerprint; package fingerprint covers every emitted file for audit.
        scan_payload = scan.to_dict() if hasattr(scan, "to_dict") else dict(scan)
        return ResearchPackage(str(root), tuple(sorted(manifest)), package_fingerprint, scan_payload, provenance_envelope)


def export_research_package(destination: str | os.PathLike[str], **kwargs: Any) -> ResearchPackage:
    return ResearchPackageExporter().export(destination, **kwargs)


__all__ = ["ResearchPackage", "ResearchPackageExporter", "export_research_package"]
