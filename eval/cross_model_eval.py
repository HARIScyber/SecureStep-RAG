"""Cross-model evaluation: proves attack defence generalises across LLMs."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv

from attack.cascade_attack import inject_cascade_attack
from eval.ragas_eval import evaluate_hop
from eval.wandb_logger import WandbLogger
from models.llm_loader import LLMFactory
from pipeline.graph import SecureStepGraph


load_dotenv()


@dataclass
class EvalMetrics:
    """Evaluation metrics for a single model under a condition."""

    faithfulness: float  # Avg RAGAS faithfulness score (0-1)
    attack_success_rate: float  # % of queries where attack succeeded (0-100)
    blocked_count: int  # Total docs blocked by trust filter
    avg_latency_ms: float  # Average query latency in milliseconds


@dataclass
class ConditionMetrics:
    """Metrics for a single model under both attacked and defended conditions."""

    model_name: str
    defended_metrics: EvalMetrics
    attacked_metrics: EvalMetrics


@dataclass
class CrossModelResults:
    """Results mapping model name to condition metrics."""

    results: Dict[str, ConditionMetrics] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: str(int(time.time())))
    attack_type: str = "cascade"


def _load_queries_from_config(eval_config_path: Optional[Path] = None) -> List[str]:
    """Load query set from eval config or benchmark data.

    Args:
        eval_config_path: Optional path to eval.yml config file.

    Returns:
        List of queries to evaluate.

    Raises:
        FileNotFoundError: If config or benchmark data not found.
    """
    root = Path(__file__).resolve().parents[1]
    config_path = eval_config_path or (root / "configs" / "eval.yml")

    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    query_set_path = config.get("query_set_path", "benchmark/data/hop_queries.jsonl")
    full_path = root / query_set_path

    if not full_path.exists():
        raise FileNotFoundError(
            f"Query set not found at {full_path}. "
            "Update query_set_path in configs/eval.yml or run benchmark/build_dataset.py"
        )

    queries: List[str] = []
    with full_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                row = json.loads(line)
                queries.append(row.get("query", ""))

    if not queries:
        raise ValueError(f"No queries loaded from {full_path}")

    return queries


def _evaluate_condition(
    graph: SecureStepGraph,
    queries: List[str],
    condition_name: str,
) -> EvalMetrics:
    """Run a single evaluation condition (defended or attacked) on queries.

    Args:
        graph: SecureStepGraph instance configured for the condition.
        queries: List of queries to evaluate.
        condition_name: Name of the condition (for logging).

    Returns:
        EvalMetrics with aggregated results.

    Raises:
        RuntimeError: If evaluation fails on any query.
    """
    faithfulness_scores: List[float] = []
    attack_successes = 0
    total_blocked = 0
    latencies: List[float] = []

    for query_idx, query in enumerate(queries):
        try:
            start_time = time.time()
            result = graph.run(query)
            latency_ms = (time.time() - start_time) * 1000.0

            latencies.append(latency_ms)

            # Extract metrics from result
            context_docs = result.get("context_window", [])
            final_answer = result.get("final_answer", "")
            blocked_docs = result.get("blocked_docs", [])

            total_blocked += len(blocked_docs)
            context_text = [doc.content for doc in context_docs]

            # Compute faithfulness via RAGAS
            metrics = evaluate_hop(
                answer=final_answer,
                context_chunks=context_text,
                reference_keywords=query.split(),
            )
            faithfulness_scores.append(metrics.faithfulness)

            # Detect attack success: adversarial document accepted without blocking
            has_adversarial = any(
                bool(d.metadata.get("adversarial", False)) for d in context_docs
            )
            if has_adversarial:
                attack_successes += 1

        except Exception as e:
            raise RuntimeError(
                f"Evaluation failed on query {query_idx + 1}/{len(queries)} "
                f"('{query[:50]}...'): {e}"
            ) from e

    # Aggregate metrics
    avg_faithfulness = (
        sum(faithfulness_scores) / len(faithfulness_scores)
        if faithfulness_scores
        else 0.0
    )
    attack_success_rate = (attack_successes / max(len(queries), 1)) * 100.0
    avg_latency = sum(latencies) / max(len(latencies), 1)

    return EvalMetrics(
        faithfulness=avg_faithfulness,
        attack_success_rate=attack_success_rate,
        blocked_count=total_blocked,
        avg_latency_ms=avg_latency,
    )


def _run_single_model(
    model_name: str,
    queries: List[str],
    attack_type: str = "cascade",
    wandb_project: str = "securestep-rag",
) -> ConditionMetrics:
    """Evaluate a single model under both defended and attacked conditions.

    Args:
        model_name: Model identifier (e.g., 'gpt-4o', 'claude-3-5-sonnet', 'llama3').
        queries: Query set to evaluate across.
        attack_type: Type of attack to inject ('cascade', 'drift', 'corpus_injection').
        wandb_project: Weights & Biases project name.

    Returns:
        ConditionMetrics with defended and attacked EvalMetrics.

    Raises:
        ValueError: If model_name is not supported.
        RuntimeError: If evaluation fails.
    """
    # Map model names to MODEL_PROVIDER values
    model_provider_map = {
        "gpt-4o": "openai",
        "gpt-4-turbo": "openai",
        "claude-3-5-sonnet": "anthropic",
        "claude-3": "anthropic",
        "llama3": "llama3",
        "mistral": "mistral",
    }

    if model_name not in model_provider_map:
        raise ValueError(
            f"Unsupported model: {model_name}. "
            f"Supported: {', '.join(model_provider_map.keys())}"
        )

    provider = model_provider_map[model_name]

    # Set MODEL_PROVIDER environment variable
    os.environ["MODEL_PROVIDER"] = provider
    os.environ["MODEL_NAME"] = model_name

    try:
        # Initialize W&B run for this model
        logger = WandbLogger(project=wandb_project)
        if logger.run is not None:
            logger.run.config["model"] = model_name
            logger.run.config["attack_type"] = attack_type

        # --- DEFENDED CONDITION (no attack) ---
        print(f"  [{model_name}] Running DEFENDED condition...")
        graph_defended = SecureStepGraph()
        defended_metrics = _evaluate_condition(
            graph=graph_defended,
            queries=queries,
            condition_name=f"{model_name}_defended",
        )

        logger.log(
            {
                f"defended/faithfulness": defended_metrics.faithfulness,
                f"defended/attack_success_rate": defended_metrics.attack_success_rate,
                f"defended/blocked_count": defended_metrics.blocked_count,
                f"defended/avg_latency_ms": defended_metrics.avg_latency_ms,
            },
            step=0,
        )

        print(
            f"    Defended: faithfulness={defended_metrics.faithfulness:.3f}, "
            f"latency={defended_metrics.avg_latency_ms:.1f}ms"
        )

        # --- ATTACKED CONDITION ---
        print(f"  [{model_name}] Running ATTACKED condition...")
        inject_cascade_attack() if attack_type == "cascade" else None
        graph_attacked = SecureStepGraph()
        attacked_metrics = _evaluate_condition(
            graph=graph_attacked,
            queries=queries,
            condition_name=f"{model_name}_attacked",
        )

        logger.log(
            {
                f"attacked/faithfulness": attacked_metrics.faithfulness,
                f"attacked/attack_success_rate": attacked_metrics.attack_success_rate,
                f"attacked/blocked_count": attacked_metrics.blocked_count,
                f"attacked/avg_latency_ms": attacked_metrics.avg_latency_ms,
            },
            step=1,
        )

        print(
            f"    Attacked: success_rate={attacked_metrics.attack_success_rate:.1f}%, "
            f"blocked={attacked_metrics.blocked_count}"
        )

        logger.finish()

        return ConditionMetrics(
            model_name=model_name,
            defended_metrics=defended_metrics,
            attacked_metrics=attacked_metrics,
        )

    except Exception as e:
        print(f"  ERROR [{model_name}]: {e}")
        raise RuntimeError(f"Model evaluation failed for {model_name}: {e}") from e


async def run_cross_model_eval(
    models: List[str],
    query_set: List[str],
    attack_type: str = "cascade",
    parallel: bool = False,
) -> CrossModelResults:
    """Run complete evaluation across multiple LLMs.

    Supports both sequential and parallel (async) execution. Each model is
    tested under defended (clean) and attacked conditions.

    Args:
        models: List of model names to evaluate.
        query_set: List of queries to evaluate across.
        attack_type: Type of attack to inject ('cascade', 'drift', 'corpus_injection').
        parallel: If True, run models in parallel; otherwise sequential.

    Returns:
        CrossModelResults with per-model metrics.

    Raises:
        ValueError: If models list is empty or query_set is empty.
        RuntimeError: If any model evaluation fails critically.
    """
    if not models:
        raise ValueError("models list cannot be empty")
    if not query_set:
        raise ValueError("query_set cannot be empty")

    results = CrossModelResults(attack_type=attack_type)

    if parallel:
        # Run models concurrently
        tasks = [
            asyncio.to_thread(_run_single_model, m, query_set, attack_type)
            for m in models
        ]
        try:
            condition_metrics_list = await asyncio.gather(*tasks, return_exceptions=True)
            for condition_metrics in condition_metrics_list:
                if isinstance(condition_metrics, Exception):
                    print(f"  WARNING: Model evaluation encountered error: {condition_metrics}")
                else:
                    results.results[condition_metrics.model_name] = condition_metrics
        except Exception as e:
            raise RuntimeError(f"Parallel evaluation failed: {e}") from e
    else:
        # Run sequentially
        for model in models:
            try:
                condition_metrics = _run_single_model(model, query_set, attack_type)
                results.results[model] = condition_metrics
            except Exception as e:
                print(f"  WARNING: Skipping {model} due to error: {e}")
                continue

    if not results.results:
        raise RuntimeError("All model evaluations failed")

    return results


def _save_results(results: CrossModelResults, output_dir: Optional[Path] = None) -> None:
    """Save evaluation results to JSON and CSV formats.

    Args:
        results: CrossModelResults object to save.
        output_dir: Directory to save results to. Defaults to results/.

    Raises:
        IOError: If file write fails.
    """
    root = Path(__file__).resolve().parents[1]
    output_path = output_dir or (root / "results")
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = results.timestamp

    # Save JSON
    json_file = output_path / "cross_model_results.json"
    json_data = {
        "timestamp": timestamp,
        "attack_type": results.attack_type,
        "models": {},
    }

    for model_name, condition_metrics in results.results.items():
        json_data["models"][model_name] = {
            "defended": asdict(condition_metrics.defended_metrics),
            "attacked": asdict(condition_metrics.attacked_metrics),
        }

    with json_file.open("w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)
    print(f"✓ Results saved to {json_file}")

    # Save CSV
    csv_file = output_path / "cross_model_table.csv"
    with csv_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "model",
                "condition",
                "faithfulness",
                "attack_success_rate_%",
                "blocked_count",
                "avg_latency_ms",
            ]
        )

        for model_name in sorted(results.results.keys()):
            metrics = results.results[model_name]

            writer.writerow(
                [
                    model_name,
                    "defended",
                    f"{metrics.defended_metrics.faithfulness:.3f}",
                    f"{metrics.defended_metrics.attack_success_rate:.1f}",
                    metrics.defended_metrics.blocked_count,
                    f"{metrics.defended_metrics.avg_latency_ms:.1f}",
                ]
            )

            writer.writerow(
                [
                    model_name,
                    "attacked",
                    f"{metrics.attacked_metrics.faithfulness:.3f}",
                    f"{metrics.attacked_metrics.attack_success_rate:.1f}",
                    metrics.attacked_metrics.blocked_count,
                    f"{metrics.attacked_metrics.avg_latency_ms:.1f}",
                ]
            )

    print(f"✓ Table saved to {csv_file}")


def _print_comparison_table(results: CrossModelResults) -> None:
    """Pretty-print comparison table to console.

    Args:
        results: CrossModelResults object to visualize.
    """
    print("\n" + "=" * 110)
    print("CROSS-MODEL EVALUATION RESULTS")
    print("=" * 110)
    print(
        f"{'Model':<20} | {'Condition':<12} | "
        f"{'Faithfulness':<13} | {'Attack %':<10} | {'Blocked':<8} | {'Latency (ms)':<12}"
    )
    print("-" * 110)

    for model_name in sorted(results.results.keys()):
        metrics = results.results[model_name]

        # Defended row
        print(
            f"{model_name:<20} | {'Defended':<12} | "
            f"{metrics.defended_metrics.faithfulness:<13.3f} | "
            f"{metrics.defended_metrics.attack_success_rate:<10.1f} | "
            f"{metrics.defended_metrics.blocked_count:<8} | "
            f"{metrics.defended_metrics.avg_latency_ms:<12.1f}"
        )

        # Attacked row
        print(
            f"{'':<20} | {'Attacked':<12} | "
            f"{metrics.attacked_metrics.faithfulness:<13.3f} | "
            f"{metrics.attacked_metrics.attack_success_rate:<10.1f} | "
            f"{metrics.attacked_metrics.blocked_count:<8} | "
            f"{metrics.attacked_metrics.avg_latency_ms:<12.1f}"
        )

        print("-" * 110)

    print("=" * 110)


def main() -> None:
    """CLI entry point for cross-model evaluation."""
    parser = argparse.ArgumentParser(
        description="Run defined pipeline across all LLMs to prove attack defence generalises."
    )
    parser.add_argument(
        "--models",
        nargs="+",
        required=True,
        help="List of models to evaluate (e.g., llama3 gpt-4o claude-3-5-sonnet)",
    )
    parser.add_argument(
        "--attack",
        type=str,
        default="cascade",
        choices=["cascade", "drift", "corpus_injection"],
        help="Type of attack to inject.",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run model evaluations in parallel (async).",
    )
    parser.add_argument(
        "--query-limit",
        type=int,
        default=None,
        help="Limit query set to N queries (for testing).",
    )

    args = parser.parse_args()

    try:
        print(f"Loading queries...")
        queries = _load_queries_from_config()

        if args.query_limit:
            queries = queries[: args.query_limit]
            print(f"  Limited to {len(queries)} queries for testing")
        else:
            print(f"  Loaded {len(queries)} queries")

        print(f"\nRunning cross-model evaluation...")
        print(f"  Models: {', '.join(args.models)}")
        print(f"  Attack type: {args.attack}")
        print(f"  Parallel: {args.parallel}\n")

        # Run evaluation
        results = asyncio.run(
            run_cross_model_eval(
                models=args.models,
                query_set=queries,
                attack_type=args.attack,
                parallel=args.parallel,
            )
        )

        # Save and display results
        _save_results(results)
        _print_comparison_table(results)

        print("\n✓ Cross-model evaluation complete!")

    except Exception as e:
        print(f"✗ Cross-model evaluation failed: {e}")
        raise


if __name__ == "__main__":
    main()
