"""Naive RAG baseline without trust filter or guardrails for comparison."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import yaml

from eval.ragas_eval import evaluate_hop
from eval.wandb_logger import WandbLogger
from pipeline.graph import SecureStepGraph


@dataclass
class BaselineResult:
    """Result metrics from naive RAG baseline evaluation.
    
    Attributes:
        faithfulness_score: Average RAGAS faithfulness metric (0-100).
        attack_success_rate: Percentage of queries accepting adversarial content (0-100).
        avg_hops: Average number of retrieval hops per query.
        blocked_docs: Number of documents blocked by trust filter (0 for baseline).
    """

    faithfulness_score: float
    attack_success_rate: float
    avg_hops: float
    blocked_docs: int = 0


class NaiveRAGBaseline:
    """Naive RAG baseline with all defenses disabled.
    
    This baseline runs the same LangGraph pipeline as the defended conditions
    but with trust_threshold set to 0.0, effectively disabling the trust filter
    and allowing all retrieved documents to pass through unfiltered.
    
    Attributes:
        graph: The SecureStepGraph pipeline instance with disabled filtering.
        logger: W&B logger for tracking metrics.
    """

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """Initialize the naive RAG baseline with disabled trust filtering.
        
        Args:
            config_path: Optional path to pipeline config. Defaults to configs/pipeline.yml.
        """
        self.graph = SecureStepGraph(config_path=config_path)
        # Disable trust filter by setting threshold to 0.0 (pass all docs)
        self.graph.config.trust_threshold = 0.0
        self.logger = WandbLogger(project="securestep-rag")

    def run(self, query_set: List[str]) -> BaselineResult:
        """Execute baseline RAG pipeline on a set of queries.
        
        Args:
            query_set: List of queries to evaluate.
            
        Returns:
            BaselineResult with aggregated faithfulness, attack success rate,
            and hop statistics.
            
        Raises:
            ValueError: If query_set is empty.
            RuntimeError: If pipeline execution fails on any query.
        """
        if not query_set:
            raise ValueError("query_set cannot be empty")

        faithfulness_scores: List[float] = []
        hop_counts: List[int] = []
        attack_successes = 0

        for query_idx, query in enumerate(query_set):
            try:
                # Run the pipeline with disabled trust filter
                result = self.graph.run(query)

                # Extract metrics from pipeline output
                context = [doc.content for doc in result.get("context_window", [])]
                answer = result.get("final_answer", "")
                hop_count = result.get("hop_count", 0)

                # Evaluate faithfulness using RAGAS metrics
                metrics = evaluate_hop(
                    answer=answer,
                    context_chunks=context,
                    reference_keywords=query.split(),
                )
                faithfulness_scores.append(metrics.faithfulness)
                hop_counts.append(hop_count)

                # Check for attack success: adversarial docs in retrieved context
                accepted_adv = any(
                    bool(d.metadata.get("adversarial", False))
                    for d in result.get("context_window", [])
                )
                if accepted_adv:
                    attack_successes += 1

                # Log intermediate metrics to W&B
                self.logger.log(
                    metrics={
                        "query_idx": query_idx,
                        "faithfulness": metrics.faithfulness,
                        "hop_count": hop_count,
                        "adversarial_accepted": float(accepted_adv),
                    },
                    step=query_idx,
                )

            except Exception as e:
                raise RuntimeError(f"Pipeline execution failed on query {query_idx}: {e}") from e

        # Compute aggregated metrics
        avg_faithfulness = sum(faithfulness_scores) / max(len(faithfulness_scores), 1)
        avg_hop_count = sum(hop_counts) / max(len(hop_counts), 1)
        attack_success_rate = (attack_successes / max(len(query_set), 1)) * 100.0

        # Create result object
        result = BaselineResult(
            faithfulness_score=avg_faithfulness,
            attack_success_rate=attack_success_rate,
            avg_hops=avg_hop_count,
            blocked_docs=0,  # No filtering, so nothing is blocked
        )

        self.logger.finish()
        return result


def _load_queries_from_config() -> List[str]:
    """Load evaluation queries from configs/eval.yml.
    
    Returns:
        List of evaluation queries.
        
    Raises:
        FileNotFoundError: If eval.yml cannot be found.
    """
    root = Path(__file__).resolve().parents[1]
    config_path = root / "configs" / "eval.yml"

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    query_set = config.get("evaluation", {}).get("query_set", [])
    if not query_set:
        raise ValueError("No queries found in configs/eval.yml:evaluation.query_set")

    return query_set


def _save_results(result: BaselineResult, output_path: Optional[Path] = None) -> Path:
    """Save baseline results to JSON file.
    
    Args:
        result: The BaselineResult to save.
        output_path: Optional custom output path. Defaults to results/baseline_results.json.
        
    Returns:
        Path where results were saved.
        
    Raises:
        IOError: If file write fails.
    """
    if output_path is None:
        root = Path(__file__).resolve().parents[1]
        output_path = root / "results" / "baseline_results.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    result_dict = {
        "condition": "naive_rag_no_defence",
        "faithfulness_score": result.faithfulness_score,
        "attack_success_rate": result.attack_success_rate,
        "avg_hops": result.avg_hops,
        "blocked_docs": result.blocked_docs,
    }

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result_dict, f, indent=2)

    return output_path


def main() -> None:
    """Run baseline evaluation and save results."""
    try:
        # Load queries from config
        queries = _load_queries_from_config()
        print(f"Loaded {len(queries)} evaluation queries from configs/eval.yml")

        # Run baseline
        print("Running naive RAG baseline (no trust filter, no guardrails)...")
        baseline = NaiveRAGBaseline()
        result = baseline.run(queries)

        # Save results
        output_file = _save_results(result)
        print(f"\nBaseline Results:")
        print(f"  Faithfulness Score: {result.faithfulness_score:.2f}")
        print(f"  Attack Success Rate: {result.attack_success_rate:.2f}%")
        print(f"  Average Hops: {result.avg_hops:.2f}")
        print(f"  Blocked Documents: {result.blocked_docs}")
        print(f"\nResults saved to: {output_file}")

    except Exception as e:
        print(f"Error running baseline: {e}")
        raise


if __name__ == "__main__":
    main()
