"""Auto-calibrate trust filter threshold using labeled held-out dataset."""

from __future__ import annotations

import json
import logging
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import yaml
from sklearn.metrics import auc, f1_score, precision_recall_curve, roc_curve

from pipeline.retriever import RetrievedDocument
from trust_filter.filter import TrustFilter

logger = logging.getLogger(__name__)


@dataclass
class ThresholdMetrics:
    """Metrics at a specific threshold value."""

    threshold: float
    tp: int
    fp: int
    tn: int
    fn: int
    precision: float
    recall: float
    f1: float
    specificity: float
    fpr: float  # False positive rate
    fnr: float  # False negative rate
    accuracy: float


@dataclass
class CalibrationResult:
    """Result of threshold calibration."""

    optimal_threshold: float
    """Optimal threshold maximizing F1 while keeping FPR < 0.05."""

    f1_at_threshold: float
    """F1 score at optimal threshold."""

    precision: float
    """Precision at optimal threshold."""

    recall: float
    """Recall at optimal threshold."""

    specificity: float
    """Specificity (true negative rate) at optimal threshold."""

    fpr: float
    """False positive rate at optimal threshold."""

    fnr: float
    """False negative rate at optimal threshold."""

    roc_auc: float
    """Area under ROC curve (0-1)."""

    threshold_curve: List[Dict[str, float]] = field(default_factory=list)
    """Threshold sweep results: [{'threshold': x, 'f1': y, 'fpr': z, ...}]."""

    roc_points: List[Dict[str, float]] = field(default_factory=list)
    """ROC curve points: [{'fpr': x, 'tpr': y}]."""

    n_clean: int = 0
    """Number of clean documents in calibration set."""

    n_injected: int = 0
    """Number of injected documents in calibration set."""

    total_docs: int = 0
    """Total documents calibrated on."""


@dataclass
class SignalWeightCalibration:
    """Per-signal weight calibration results."""

    semantic_weight: float
    source_weight: float
    injection_weight: float
    hop_weight: float
    improvement_vs_baseline: float
    """F1 improvement (%) vs uniform weights."""

    per_signal_f1: Dict[str, float]
    """F1 score when each signal is dominant."""


class ThresholdCalibrator:
    """Calibrates trust filter threshold and signal weights using labeled data."""

    def __init__(
        self,
        trust_filter: Optional[TrustFilter] = None,
        seed: int = 42,
    ) -> None:
        """Initialize calibrator.

        Args:
            trust_filter: TrustFilter instance (creates new if not provided)
            seed: Random seed for reproducibility
        """
        self.trust_filter = trust_filter or TrustFilter()
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)

    def calibrate(
        self,
        clean_docs_path: str,
        injected_docs_path: str,
        fpr_threshold: float = 0.05,
        min_f1_threshold: float = 0.6,
    ) -> CalibrationResult:
        """Calibrate optimal threshold using labeled documents.

        Args:
            clean_docs_path: Path to JSONL with clean documents
            injected_docs_path: Path to JSONL with adversarial documents
            fpr_threshold: Maximum acceptable false positive rate (default 0.05 = 5%)
            min_f1_threshold: Minimum F1 score to consider (default 0.6)

        Returns:
            CalibrationResult with optimal threshold and metrics

        Raises:
            FileNotFoundError: If document paths not found
            ValueError: If insufficient documents to calibrate
        """
        logger.info("Loading calibration datasets...")
        clean_docs = self._load_jsonl(clean_docs_path)
        injected_docs = self._load_jsonl(injected_docs_path)

        if not clean_docs or not injected_docs:
            raise ValueError("Need both clean and injected documents for calibration")

        logger.info(f"Loaded {len(clean_docs)} clean documents")
        logger.info(f"Loaded {len(injected_docs)} injected documents")

        # Create labeled dataset
        labels = [0] * len(clean_docs) + [1] * len(injected_docs)
        documents = clean_docs + injected_docs
        total_docs = len(documents)

        # Score all documents
        logger.info(f"Scoring {total_docs} documents...")
        scores = self._score_all_documents(documents)

        # Sweep thresholds
        logger.info("Sweeping thresholds 0-100...")
        threshold_metrics = self._sweep_thresholds(scores, labels)

        # Find optimal threshold
        optimal_result = self._find_optimal_threshold(
            threshold_metrics,
            fpr_threshold=fpr_threshold,
            min_f1=min_f1_threshold,
        )

        # Compute ROC curve
        logger.info("Computing ROC curve...")
        fpr, tpr, roc_thresholds = roc_curve(labels, scores)
        roc_auc = auc(fpr, tpr)

        roc_points = [
            {"fpr": float(f), "tpr": float(t)} for f, t in zip(fpr, tpr)
        ]

        # Build result
        result = CalibrationResult(
            optimal_threshold=optimal_result.threshold,
            f1_at_threshold=optimal_result.f1,
            precision=optimal_result.precision,
            recall=optimal_result.recall,
            specificity=optimal_result.specificity,
            fpr=optimal_result.fpr,
            fnr=optimal_result.fnr,
            roc_auc=roc_auc,
            threshold_curve=[asdict(m) for m in threshold_metrics],
            roc_points=roc_points,
            n_clean=len(clean_docs),
            n_injected=len(injected_docs),
            total_docs=total_docs,
        )

        logger.info(f"Optimal threshold: {result.optimal_threshold:.1f}")
        logger.info(f"F1 at threshold: {result.f1_at_threshold:.4f}")
        logger.info(f"FPR at threshold: {result.fpr:.4f} (target: < {fpr_threshold})")

        return result

    def calibrate_per_signal(
        self,
        clean_docs_path: str,
        injected_docs_path: str,
    ) -> SignalWeightCalibration:
        """Calibrate weights for individual trust signals.

        Args:
            clean_docs_path: Path to JSONL with clean documents
            injected_docs_path: Path to JSONL with adversarial documents

        Returns:
            SignalWeightCalibration with optimal weights per signal

        Note:
            Uses grid search over weight combinations that sum to 1.0
        """
        logger.info("Loading documents for signal weight calibration...")
        clean_docs = self._load_jsonl(clean_docs_path)
        injected_docs = self._load_jsonl(injected_docs_path)

        labels = [0] * len(clean_docs) + [1] * len(injected_docs)
        documents = clean_docs + injected_docs

        # Score individual signals
        logger.info("Scoring individual signals...")
        signal_scores = self._score_all_signals(documents)

        # Grid search over weight combinations
        logger.info("Grid searching weight combinations...")
        best_f1 = -1.0
        best_weights = {"semantic": 0.25, "source": 0.25, "injection": 0.25, "hop": 0.25}
        per_signal_f1 = {}

        # Test each signal individually (baseline)
        for signal in ["semantic", "source", "injection", "hop"]:
            weights = {s: (1.0 if s == signal else 0.0) for s in signal_scores}
            combined = self._combine_signals(signal_scores, weights)
            f1 = f1_score(labels, [1 if s >= 50 else 0 for s in combined])
            per_signal_f1[signal] = f1

        # Grid search: step=0.1 for faster convergence
        for s_w in np.arange(0.0, 1.0, 0.1):
            for src_w in np.arange(0.0, 1.0 - s_w, 0.1):
                for inj_w in np.arange(0.0, 1.0 - s_w - src_w, 0.1):
                    h_w = 1.0 - s_w - src_w - inj_w

                    weights = {
                        "semantic": float(s_w),
                        "source": float(src_w),
                        "injection": float(inj_w),
                        "hop": float(h_w),
                    }

                    combined = self._combine_signals(signal_scores, weights)
                    f1 = f1_score(labels, [1 if s >= 50 else 0 for s in combined])

                    if f1 > best_f1:
                        best_f1 = f1
                        best_weights = weights

        # Compute baseline F1 with uniform weights
        uniform_weights = {s: 0.25 for s in signal_scores}
        uniform_combined = self._combine_signals(signal_scores, uniform_weights)
        baseline_f1 = f1_score(labels, [1 if s >= 50 else 0 for s in uniform_combined])

        improvement = ((best_f1 - baseline_f1) / baseline_f1) * 100 if baseline_f1 > 0 else 0

        return SignalWeightCalibration(
            semantic_weight=best_weights["semantic"],
            source_weight=best_weights["source"],
            injection_weight=best_weights["injection"],
            hop_weight=best_weights["hop"],
            improvement_vs_baseline=improvement,
            per_signal_f1=per_signal_f1,
        )

    def plot_roc_curve(
        self,
        result: CalibrationResult,
        output_path: str = "results/roc_curve.png",
    ) -> None:
        """Plot ROC curve and save to file.

        Args:
            result: CalibrationResult from calibrate()
            output_path: Where to save the plot
        """
        plt.figure(figsize=(10, 8))

        fpr = [p["fpr"] for p in result.roc_points]
        tpr = [p["tpr"] for p in result.roc_points]

        plt.plot(fpr, tpr, "b-", linewidth=2, label=f"ROC (AUC = {result.roc_auc:.3f})")
        plt.plot([0, 1], [0, 1], "r--", linewidth=1, label="Random Classifier")

        plt.scatter(
            [result.fpr],
            [1 - result.fnr],
            color="green",
            s=100,
            zorder=5,
            label=f"Optimal (threshold={result.optimal_threshold:.0f})",
        )

        plt.xlabel("False Positive Rate", fontsize=12)
        plt.ylabel("True Positive Rate (Recall)", fontsize=12)
        plt.title("ROC Curve: Trust Filter Calibration", fontsize=14, fontweight="bold")
        plt.legend(fontsize=11)
        plt.grid(True, alpha=0.3)
        plt.xlim([0, 1])
        plt.ylim([0, 1])

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info(f"ROC curve saved to {output_path}")
        plt.close()

    def plot_threshold_curve(
        self,
        result: CalibrationResult,
        output_path: str = "results/threshold_curve.png",
    ) -> None:
        """Plot threshold vs metrics and save to file.

        Args:
            result: CalibrationResult from calibrate()
            output_path: Where to save the plot
        """
        thresholds = [m["threshold"] for m in result.threshold_curve]
        f1_scores = [m["f1"] for m in result.threshold_curve]
        fprs = [m["fpr"] for m in result.threshold_curve]
        precisions = [m["precision"] for m in result.threshold_curve]
        recalls = [m["recall"] for m in result.threshold_curve]

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

        # Plot 1: F1 and FPR vs Threshold
        ax1.plot(thresholds, f1_scores, "b-", linewidth=2, label="F1 Score")
        ax1.plot(thresholds, fprs, "r-", linewidth=2, label="False Positive Rate")
        ax1.axhline(y=0.05, color="r", linestyle="--", alpha=0.5, label="FPR Threshold (0.05)")
        ax1.axvline(x=result.optimal_threshold, color="g", linestyle="--", linewidth=2,
                   label=f"Optimal Threshold ({result.optimal_threshold:.0f})")

        ax1.scatter([result.optimal_threshold], [result.f1_at_threshold],
                   color="green", s=100, zorder=5)
        ax1.set_xlabel("Threshold", fontsize=11)
        ax1.set_ylabel("Score", fontsize=11)
        ax1.set_title("F1 Score and FPR vs Threshold", fontsize=12, fontweight="bold")
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim([0, 100])

        # Plot 2: Precision-Recall vs Threshold
        ax2.plot(thresholds, precisions, "purple", linewidth=2, label="Precision")
        ax2.plot(thresholds, recalls, "orange", linewidth=2, label="Recall")
        ax2.axvline(x=result.optimal_threshold, color="g", linestyle="--", linewidth=2,
                   label=f"Optimal Threshold ({result.optimal_threshold:.0f})")
        ax2.scatter([result.optimal_threshold], [result.precision],
                   color="purple", s=100, zorder=5)
        ax2.scatter([result.optimal_threshold], [result.recall],
                   color="orange", s=100, zorder=5)

        ax2.set_xlabel("Threshold", fontsize=11)
        ax2.set_ylabel("Score", fontsize=11)
        ax2.set_title("Precision and Recall vs Threshold", fontsize=12, fontweight="bold")
        ax2.legend(fontsize=10)
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim([0, 100])

        plt.tight_layout()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info(f"Threshold curve saved to {output_path}")
        plt.close()

    def update_config(
        self,
        result: CalibrationResult,
        config_path: Optional[str] = None,
    ) -> None:
        """Update pipeline config with calibrated threshold.

        Args:
            result: CalibrationResult from calibrate()
            config_path: Path to pipeline.yml (uses default if not provided)
        """
        base = Path(__file__).resolve().parents[1]
        cfg_path = Path(config_path or base / "configs" / "pipeline.yml")

        with cfg_path.open("r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        old_threshold = config["pipeline"]["trust_threshold"]
        config["pipeline"]["trust_threshold"] = int(result.optimal_threshold)

        with cfg_path.open("w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False)

        logger.info(f"Updated {cfg_path}: threshold {old_threshold} → {int(result.optimal_threshold)}")

    def save_results(
        self,
        result: CalibrationResult,
        output_path: str = "results/calibration_results.json",
    ) -> None:
        """Save calibration results to JSON.

        Args:
            result: CalibrationResult from calibrate()
            output_path: Where to save the JSON
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        output = {
            "optimal_threshold": result.optimal_threshold,
            "metrics": {
                "f1": result.f1_at_threshold,
                "precision": result.precision,
                "recall": result.recall,
                "specificity": result.specificity,
                "fpr": result.fpr,
                "fnr": result.fnr,
                "roc_auc": result.roc_auc,
            },
            "dataset": {
                "n_clean": result.n_clean,
                "n_injected": result.n_injected,
                "total": result.total_docs,
            },
            "threshold_curve": result.threshold_curve,
            "roc_curve": result.roc_points,
            "seed": self.seed,
        }

        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)

        logger.info(f"Calibration results saved to {output_path}")

    # Private methods

    def _load_jsonl(self, path: str) -> List[Dict[str, Any]]:
        """Load JSONL documents."""
        documents = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        documents.append(json.loads(line))
        except FileNotFoundError:
            raise FileNotFoundError(f"Document file not found: {path}")

        return documents

    def _score_all_documents(self, documents: List[Dict[str, Any]]) -> List[float]:
        """Score all documents using trust filter."""
        scores = []

        for doc in documents:
            try:
                # Create RetrievedDocument
                retrieved_doc = RetrievedDocument(
                    content=doc.get("content", ""),
                    source=doc.get("source", "unknown"),
                    source_type=doc.get("source_type", "web"),
                    credibility=doc.get("credibility", 0.5),
                    metadata={"topic": doc.get("topic", ""), "adversarial": doc.get("adversarial", False)},
                )

                # Use topic as synthetic query
                query = f"Tell me about {doc.get('topic', 'topic')}"

                # Score the document
                trust_score = self.trust_filter.score(
                    doc=retrieved_doc,
                    query=query,
                    hop_history=[],
                    accepted_docs=None,
                )

                scores.append(trust_score.total)

            except Exception as e:
                logger.warning(f"Failed to score document: {e}")
                scores.append(50.0)  # Default score if scoring fails

        return scores

    def _score_all_signals(self, documents: List[Dict[str, Any]]) -> Dict[str, List[float]]:
        """Score individual trust signals."""
        signal_scores = {"semantic": [], "source": [], "injection": [], "hop": []}

        for doc in documents:
            try:
                retrieved_doc = RetrievedDocument(
                    content=doc.get("content", ""),
                    source=doc.get("source", "unknown"),
                    source_type=doc.get("source_type", "web"),
                    credibility=doc.get("credibility", 0.5),
                    metadata={"topic": doc.get("topic", "")},
                )

                query = f"Tell me about {doc.get('topic', 'topic')}"

                trust_score = self.trust_filter.score(
                    doc=retrieved_doc,
                    query=query,
                    hop_history=[],
                    accepted_docs=None,
                )

                signal_scores["semantic"].append(trust_score.semantic)
                signal_scores["source"].append(trust_score.source)
                signal_scores["injection"].append(trust_score.injection)
                signal_scores["hop"].append(trust_score.hop)

            except Exception as e:
                logger.warning(f"Failed to score document signals: {e}")
                for signal in signal_scores:
                    signal_scores[signal].append(50.0)

        return signal_scores

    def _combine_signals(
        self,
        signal_scores: Dict[str, List[float]],
        weights: Dict[str, float],
    ) -> List[float]:
        """Combine individual signals using weights."""
        combined = []
        n_docs = len(signal_scores["semantic"])

        for i in range(n_docs):
            score = (
                signal_scores["semantic"][i] * weights["semantic"]
                + signal_scores["source"][i] * weights["source"]
                + signal_scores["injection"][i] * weights["injection"]
                + signal_scores["hop"][i] * weights["hop"]
            )
            combined.append(max(0.0, min(100.0, score)))

        return combined

    def _sweep_thresholds(
        self,
        scores: List[float],
        labels: List[int],
        step: int = 1,
    ) -> List[ThresholdMetrics]:
        """Sweep thresholds and compute metrics at each."""
        results = []

        for threshold in range(0, 101, step):
            predictions = [1 if s >= threshold else 0 for s in scores]

            tp = sum(p == 1 and l == 1 for p, l in zip(predictions, labels))
            tn = sum(p == 0 and l == 0 for p, l in zip(predictions, labels))
            fp = sum(p == 1 and l == 0 for p, l in zip(predictions, labels))
            fn = sum(p == 0 and l == 1 for p, l in zip(predictions, labels))

            # Handle edge cases
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
            fnr = fn / (tp + fn) if (tp + fn) > 0 else 0.0
            accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0

            results.append(
                ThresholdMetrics(
                    threshold=float(threshold),
                    tp=tp,
                    fp=fp,
                    tn=tn,
                    fn=fn,
                    precision=precision,
                    recall=recall,
                    f1=f1,
                    specificity=specificity,
                    fpr=fpr,
                    fnr=fnr,
                    accuracy=accuracy,
                )
            )

        return results

    def _find_optimal_threshold(
        self,
        metrics_list: List[ThresholdMetrics],
        fpr_threshold: float = 0.05,
        min_f1: float = 0.6,
    ) -> ThresholdMetrics:
        """Find optimal threshold maximizing F1 while keeping FPR < threshold.

        Strategy:
        1. Filter to thresholds where FPR < fpr_threshold
        2. Among those, select max F1
        3. If none pass FPR constraint, select where F1 >= min_f1 and FPR is minimized
        """
        # Filter by FPR constraint
        valid = [m for m in metrics_list if m.fpr <= fpr_threshold]

        if valid:
            # Choose highest F1 among valid thresholds
            return max(valid, key=lambda m: m.f1)

        # Fallback: choose where F1 >= min_f1 with lowest FPR
        fallback = [m for m in metrics_list if m.f1 >= min_f1]
        if fallback:
            return min(fallback, key=lambda m: m.fpr)

        # Last resort: highest F1 overall
        return max(metrics_list, key=lambda m: m.f1)


async def main() -> None:
    """CLI entry point for threshold calibration."""
    import argparse
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Calibrate trust filter threshold using labeled documents"
    )
    parser.add_argument(
        "--clean-docs",
        type=str,
        default="benchmark/data/clean_docs.jsonl",
        help="Path to clean documents JSONL",
    )
    parser.add_argument(
        "--injected-docs",
        type=str,
        default="benchmark/data/injected_docs.jsonl",
        help="Path to injected documents JSONL",
    )
    parser.add_argument(
        "--fpr-threshold",
        type=float,
        default=0.05,
        help="Maximum acceptable FPR (default 0.05)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results/calibration_results.json",
        help="Output JSON path",
    )
    parser.add_argument(
        "--update-config",
        action="store_true",
        help="Update pipeline.yml with calibrated threshold",
    )
    parser.add_argument(
        "--calibrate-weights",
        action="store_true",
        help="Also calibrate per-signal weights",
    )

    args = parser.parse_args()

    try:
        calibrator = ThresholdCalibrator(seed=42)

        # Calibrate threshold
        logger.info("Starting threshold calibration...")
        result = calibrator.calibrate(
            clean_docs_path=args.clean_docs,
            injected_docs_path=args.injected_docs,
            fpr_threshold=args.fpr_threshold,
        )

        # Save results
        calibrator.save_results(result, output_path=args.output)

        # Generate plots
        calibrator.plot_roc_curve(result)
        calibrator.plot_threshold_curve(result)

        # Print summary
        print(
            f"\n{'='*60}\n"
            f"Calibration Complete\n"
            f"{'='*60}\n"
            f"Optimal Threshold: {result.optimal_threshold:.1f}\n"
            f"F1 Score: {result.f1_at_threshold:.4f}\n"
            f"Precision: {result.precision:.4f}\n"
            f"Recall: {result.recall:.4f}\n"
            f"FPR: {result.fpr:.4f}\n"
            f"ROC AUC: {result.roc_auc:.4f}\n"
            f"Calibrated on {result.total_docs} documents "
            f"({result.n_clean} clean, {result.n_injected} adversarial)\n"
            f"{'='*60}\n"
        )

        # Update config if requested
        if args.update_config:
            calibrator.update_config(result)
            print("✓ Updated pipeline.yml\n")

        # Calibrate weights if requested
        if args.calibrate_weights:
            logger.info("Calibrating per-signal weights...")
            weight_result = calibrator.calibrate_per_signal(
                clean_docs_path=args.clean_docs,
                injected_docs_path=args.injected_docs,
            )
            print(
                f"Per-Signal Weight Calibration\n"
                f"{'='*60}\n"
                f"Semantic: {weight_result.semantic_weight:.3f}\n"
                f"Source: {weight_result.source_weight:.3f}\n"
                f"Injection: {weight_result.injection_weight:.3f}\n"
                f"Hop: {weight_result.hop_weight:.3f}\n"
                f"Improvement vs Baseline: {weight_result.improvement_vs_baseline:+.1f}%\n"
                f"{'='*60}\n"
            )

    except Exception as e:
        logger.error(f"Calibration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
