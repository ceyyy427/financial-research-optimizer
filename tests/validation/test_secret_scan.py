from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "secret_scan.py"
SPEC = importlib.util.spec_from_file_location("finathink_secret_scan", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
secret_scan = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(secret_scan)


def test_candidate_files_ignore_all_isolated_virtualenvs(
    tmp_path: Path, monkeypatch,
) -> None:
    source = tmp_path / "src" / "module.py"
    source.parent.mkdir()
    source.write_text("print('safe')\n", encoding="utf-8")

    dependency = tmp_path / ".venv-vectorbt" / "site-packages" / "dependency.py"
    dependency.parent.mkdir(parents=True)
    # Construct the sentinel at runtime so this test does not itself look
    # like a credential to the repository scanner.
    dependency.write_text("AKIA" + ("0" * 16) + "\n", encoding="utf-8")

    monkeypatch.setattr(secret_scan, "ROOT", tmp_path)

    assert secret_scan.candidate_files() == [source]
