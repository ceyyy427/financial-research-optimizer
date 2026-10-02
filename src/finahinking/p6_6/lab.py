"""End-to-end, human-reviewed P6.6 strategy research orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from finahinking.data.models import Dataset
from finahinking.quant.multi_asset import MultiAssetDataset

from .backtest import BacktestConfiguration, run_historical_backtest, run_panel_backtest
from .compiler import compile_strategy
from .diagnostics import BacktestPaperComparison, compare_backtest_paper
from .education import EducationalCode, generate_educational_code
from .export import ResearchPackage, export_research_package
from .learning import StrategyLearningBundle, strategy_learning_bundle
from .models import StrategyIR, StrategyReview, StrategySpec
from .paper import PaperRun, PaperSimulator
from .strategy import StrategyInterpreter


@dataclass(frozen=True)
class LabRun:
    review: StrategyReview
    spec: StrategySpec
    ir: StrategyIR
    preview: Any
    historical: dict[str, Any] | None = None
    paper: PaperRun | None = None
    comparison: BacktestPaperComparison | None = None
    learning: StrategyLearningBundle | None = None
    educational_code: EducationalCode | None = None
    package: ResearchPackage | None = None

    @property
    def strategy_fingerprint(self) -> str:
        return self.spec.fingerprint

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec": self.spec.to_dict(),
            "ir": self.ir.to_dict(),
            "preview": self.preview.to_dict(),
            "historical": {key: (value.to_dict() if hasattr(value, "to_dict") else value) for key, value in (self.historical or {}).items() if key not in {"ir", "preview"}},
            "paper": self.paper.to_dict() if self.paper else None,
            "comparison": self.comparison.to_dict() if self.comparison else None,
            "learning": self.learning.to_dict() if self.learning else None,
            "package": self.package.to_dict() if self.package else None,
        }


class StrategyResearchLab:
    """Own the review gate and route execution to existing P5/P5.5 ledgers."""

    def __init__(self) -> None:
        self.interpreter = StrategyInterpreter()

    def review(self, idea: str, **kwargs: Any) -> StrategyReview:
        return self.interpreter.review(idea, **kwargs)

    def accept(self, review: StrategyReview) -> StrategySpec:
        accepted = self.interpreter.accept(review)
        return self.interpreter.build_spec(accepted)

    def prepare(self, review: StrategyReview, *, reviewed: bool = False) -> tuple[StrategySpec, StrategyIR, Any]:
        spec = self.interpreter.build_spec(review, reviewed=reviewed)
        ir, _ = compile_strategy(spec)
        from .backtest import preview_backtest

        return spec, ir, preview_backtest(spec)

    def run(
        self,
        review: StrategyReview,
        data: Dataset | MultiAssetDataset,
        *,
        config: BacktestConfiguration | None = None,
        reviewed: bool = False,
        run_id: str | None = None,
        paper: bool = False,
        export_dir: str | Path | None = None,
    ) -> LabRun:
        spec, ir, preview = self.prepare(review, reviewed=reviewed)
        if not preview.accepted:
            raise ValueError("research preview rejected: " + "; ".join(preview.rejections))
        if isinstance(data, MultiAssetDataset):
            historical = run_panel_backtest(spec, data, run_id=run_id)
            # The P5.5 panel ledger is the historical authority.  Learning and
            # educational export remain available for the panel slice; paper
            # replay is deliberately not faked as a scalar single-asset run.
            learning = strategy_learning_bundle(
                spec,
                strategy_fingerprint=spec.fingerprint,
                evidence_reference=run_id or spec.dataset_reference,
            )
            educational = generate_educational_code(spec, ir)
            package = None
            if export_dir is not None:
                package = export_research_package(
                    export_dir,
                    strategy_spec=spec,
                    feature_graph={"fingerprint": spec.feature_graph_fingerprint},
                    config=historical["experiment"].backtest.config.to_dict(),
                    research_report={
                        "backtest_fingerprint": historical["experiment"].backtest.fingerprint,
                        "limitations": list(historical["experiment"].limitations),
                    },
                    provenance={
                        "dataset_fingerprint": historical["experiment"].backtest.dataset_fingerprint,
                        "quant_run_id": historical["experiment"].quant_run.quant_run_id,
                    },
                    educational_code=educational.source,
                )
            return LabRun(
                review,
                spec,
                ir,
                preview,
                historical=historical,
                learning=learning,
                educational_code=educational,
                package=package,
            )
        historical = run_historical_backtest(spec, data, config, run_id=run_id)
        paper_run: PaperRun | None = None
        comparison: BacktestPaperComparison | None = None
        if paper:
            _, compiled = compile_strategy(spec)
            if compiled is None:
                raise ValueError("paper replay for panel strategies requires a panel replay adapter")
            paper_run = PaperSimulator().run(data, compiled, (config or BacktestConfiguration()).to_p5(), strategy_version=spec)
            comparison = compare_backtest_paper(historical["backtest"], paper_run)
        learning = strategy_learning_bundle(spec, strategy_fingerprint=spec.fingerprint, evidence_reference=run_id or spec.dataset_reference)
        educational = generate_educational_code(spec, ir)
        package = None
        if export_dir is not None:
            package = export_research_package(
                export_dir,
                strategy_spec=spec,
                feature_graph={"fingerprint": spec.feature_graph_fingerprint},
                config=(config or BacktestConfiguration()).to_dict(),
                research_report={"backtest_fingerprint": historical["backtest"].fingerprint, "limitations": list(historical["evaluation"].limitations)},
                provenance={"dataset_fingerprint": historical["backtest"].dataset_fingerprint, "quant_run_id": historical["quant_run"].quant_run_id},
                educational_code=educational.source,
            )
        return LabRun(review, spec, ir, preview, historical=historical, paper=paper_run, comparison=comparison, learning=learning, educational_code=educational, package=package)


StrategyLab = StrategyResearchLab


__all__ = ["LabRun", "StrategyLab", "StrategyResearchLab"]
