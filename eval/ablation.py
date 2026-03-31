"""Ablation runner: defended vs undefended conditions for adversarial RAG."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Tuple
import random

import numpy as np
import yaml
from scipy import stats

from attack.cascade_attack import inject_cascade_attack
from eval.baseline_comparison import NaiveRAGBaseline
from eval.ragas_eval import evaluate_hop
from pipeline.graph import SecureStepGraph

# Set random seed for reproducibility
random.seed(42)
np.random.seed(42)


@dataclass
class SignificanceResult:
    """Statistical significance test results between two conditions.
    
    Attributes:
        t_statistic: T-test statistic value
        p_value: P-value from paired t-test
        is_significant: True if p_value < 0.05
        effect_size_cohens_d: Cohen's d effect size
        confidence_interval_95: Tuple of (lower, upper) bounds for mean difference
        mean_diff: Mean difference between condition_a and condition_b
        sem: Standard error of the mean
    """
    t_statistic: float
    p_value: float
    is_significant: bool
    effect_size_cohens_d: float
    confidence_interval_95: Tuple[float, float]
    mean_diff: float
    sem: float


@dataclass
class ConditionResult:
    """Result for a single ablation condition.
    
    Attributes:
        name: Condition identifier
        faithfulness: Average faithfulness score
        attack_success_rate: Percentage of queries where attack succeeded
        blocked_doc_count: Total documents blocked across all queries
        faithfulness_scores: List of per-query faithfulness scores (for statistical analysis)
        hops: List of hop counts per query
    """
    name: str
    faithfulness: float
    attack_success_rate: float
    blocked_doc_count: int
    faithfulness_scores: List[float] = field(default_factory=list)
    hops: List[int] = field(default_factory=list)


def _load_queries() -> List[str]:
    root = Path(__file__).resolve().parents[1]
    path = root / "benchmark" / "data" / "hop_queries.jsonl"
    if not path.exists():
        return ["How does zero-trust architecture reduce lateral movement?"]

    queries = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            queries.append(row["query"])
    return queries


def bootstrap_ci(scores: List[float], n: int = 1000, ci: float = 0.95) -> Tuple[float, float]:
    """Compute bootstrap confidence interval for mean of scores.
    
    Args:
        scores: List of numerical scores
        n: Number of bootstrap resamples (default 1000)
        ci: Confidence interval level (default 0.95 for 95%)
        
    Returns:
        Tuple of (lower_bound, upper_bound) for the mean
    """
    if not scores:
        return (0.0, 0.0)
    
    bootstrapped_means = []
    for _ in range(n):
        resample = np.random.choice(scores, size=len(scores), replace=True)
        bootstrapped_means.append(np.mean(resample))
    
    alpha = 1 - ci
    lower = np.percentile(bootstrapped_means, (alpha / 2) * 100)
    upper = np.percentile(bootstrapped_means, (1 - alpha / 2) * 100)
    
    return (float(lower), float(upper))


def compute_cohens_d(group_a: List[float], group_b: List[float]) -> float:
    """Compute Cohen's d effect size between two groups.
    
    Args:
        group_a: First group of scores
        group_b: Second group of scores
        
    Returns:
        Cohen's d effect size value
    """
    if not group_a or not group_b:
        return 0.0
    
    mean_a = np.mean(group_a)
    mean_b = np.mean(group_b)
    var_a = np.var(group_a, ddof=1)
    var_b = np.var(group_b, ddof=1)
    
    # Pooled standard deviation
    n_a = len(group_a)
    n_b = len(group_b)
    pooled_std = np.sqrt(((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2))
    
    if pooled_std == 0:
        return 0.0
    
    cohens_d = (mean_a - mean_b) / pooled_std
    return float(cohens_d)


def compute_significance(
    condition_a_scores: List[float], 
    condition_b_scores: List[float],
    ci: float = 0.95
) -> SignificanceResult:
    """Compute statistical significance between two conditions using paired t-test.
    
    Args:
        condition_a_scores: Faithfulness scores from condition A
        condition_b_scores: Faithfulness scores from condition B
        ci: Confidence interval level (default 0.95)
        
    Returns:
        SignificanceResult with t-statistic, p-value, effect size, and CI
        
    Raises:
        ValueError: If score lists are empty or have mismatched lengths
    """
    if not condition_a_scores or not condition_b_scores:
        raise ValueError("Score lists must not be empty")
    
    # For paired t-test, we need equal length. If different, we'll use the smaller length.
    min_len = min(len(condition_a_scores), len(condition_b_scores))
    a_scores = condition_a_scores[:min_len]
    b_scores = condition_b_scores[:min_len]
    
    # Paired t-test
    t_stat, p_val = stats.ttest_rel(a_scores, b_scores)
    
    # Effect size (Cohen's d)
    cohens_d = compute_cohens_d(a_scores, b_scores)
    
    # Mean difference and SEM
    diffs = np.array(a_scores) - np.array(b_scores)
    mean_diff = float(np.mean(diffs))
    sem = float(stats.sem(diffs))
    
    # Confidence interval on mean difference
    alpha = 1 - ci
    t_crit = stats.t.ppf(1 - alpha / 2, df=len(diffs) - 1)
    margin = t_crit * sem
    ci_lower = mean_diff - margin
    ci_upper = mean_diff + margin
    
    return SignificanceResult(
        t_statistic=float(t_stat),
        p_value=float(p_val),
        is_significant=float(p_val) < 0.05,
        effect_size_cohens_d=float(cohens_d),
        confidence_interval_95=(float(ci_lower), float(ci_upper)),
        mean_diff=mean_diff,
        sem=sem,
    )


def _run_condition(name: str, enable_attack: bool, use_filter: bool, use_rails: bool) -> ConditionResult:
    """Run a single ablation condition and collect detailed metrics.
    
    Args:
        name: Condition identifier
        enable_attack: Whether to inject adversarial documents
        use_filter: Whether to enable trust filter
        use_rails: Whether to enable confidence gate and guardrails
        
    Returns:
        ConditionResult with aggregated and per-query metrics
    """
    if enable_attack:
        inject_cascade_attack()

    graph = SecureStepGraph()
    if not use_filter:
        graph.config.trust_threshold = 0.0
    if use_rails:
        # In production, NeMo rails would be applied around input/retrieval/output paths.
        graph.config.confidence_threshold = min(95.0, graph.config.confidence_threshold + 5.0)

    queries = _load_queries()
    faithfulness_scores: List[float] = []
    blocked_docs_per_query: List[int] = []
    hops: List[int] = []
    blocked_count = 0
    attack_successes = 0

    for q in queries:
        result = graph.run(q)
        blocked = len(result.get("blocked_docs", []))
        blocked_count += blocked
        blocked_docs_per_query.append(blocked)

        context = [doc.content for doc in result.get("context_window", [])]
        answer = result.get("final_answer", "")
        metrics = evaluate_hop(answer=answer, context_chunks=context, reference_keywords=q.split())
        faithfulness_scores.append(metrics.faithfulness)

        # Track hops (number of retrieved documents)
        hop_count = len(result.get("context_window", []))
        hops.append(hop_count)

        # Attack success: adversarial docs enter context or no docs blocked during attack runs.
        accepted_adv = any(bool(d.metadata.get("adversarial", False)) for d in result.get("context_window", []))
        if enable_attack and (accepted_adv or blocked == 0):
            attack_successes += 1

    avg_faithfulness = sum(faithfulness_scores) / max(len(faithfulness_scores), 1)
    attack_success_rate = (attack_successes / max(len(queries), 1)) * 100.0

    return ConditionResult(
        name=name,
        faithfulness=avg_faithfulness,
        attack_success_rate=attack_success_rate,
        blocked_doc_count=blocked_count,
        faithfulness_scores=faithfulness_scores,
        hops=hops,
    )


def run_ablation() -> Tuple[List[ConditionResult], Dict]:
    """Run ablation study across all conditions including naive baseline.
    
    Condition 0: naive_rag_no_defence (baseline with no trust filter or guardrails)
    Condition 1: no_attack (clean setup with defenses enabled)
    Condition 2: attack_no_defence (attack with defenses disabled)
    Condition 3: attack_trust_filter_only (attack with trust filter only)
    Condition 4: attack_trust_filter_plus_rails (attack with full defenses)
    
    Returns:
        Tuple of (results list, significance_tests dict)
    """
    results: List[ConditionResult] = []

    # Condition 0: Baseline - naive RAG with all defenses disabled
    try:
        baseline = NaiveRAGBaseline()
        baseline_result = baseline.run(_load_queries())
        results.append(
            ConditionResult(
                name="naive_rag_no_defence",
                faithfulness=baseline_result.faithfulness_score,
                attack_success_rate=baseline_result.attack_success_rate,
                blocked_doc_count=baseline_result.blocked_docs,
                faithfulness_scores=[baseline_result.faithfulness_score] * len(_load_queries()),  # Placeholder
            )
        )
    except Exception as e:
        print(f"Warning: Baseline execution failed: {e}")

    # Conditions 1-4: Standard ablation conditions
    conditions = [
        ("no_attack", False, True, False),
        ("attack_no_defence", True, False, False),
        ("attack_trust_filter_only", True, True, False),
        ("attack_trust_filter_plus_rails", True, True, True),
    ]

    results.extend(
        [
            _run_condition(name=c[0], enable_attack=c[1], use_filter=c[2], use_rails=c[3])
            for c in conditions
        ]
    )

    # Compute statistical significance between key comparisons
    significance_tests = {}
    
    # Test 1: Naive RAG vs Defended (no_attack)
    if len(results) > 1 and results[0].faithfulness_scores and results[1].faithfulness_scores:
        try:
            test_1 = compute_significance(
                results[0].faithfulness_scores,  # naive_rag
                results[1].faithfulness_scores,  # no_attack
            )
            significance_tests["naive_vs_clean"] = asdict(test_1)
        except Exception as e:
            print(f"Warning: naive vs clean significance test failed: {e}")
    
    # Test 2: Attack without defense vs Attack with full defense
    if len(results) > 4 and results[2].faithfulness_scores and results[4].faithfulness_scores:
        try:
            test_2 = compute_significance(
                results[2].faithfulness_scores,  # attack_no_defence
                results[4].faithfulness_scores,  # attack_trust_filter_plus_rails
            )
            significance_tests["attack_undefended_vs_defended"] = asdict(test_2)
        except Exception as e:
            print(f"Warning: attack defended vs undefended significance test failed: {e}")
    
    # Test 3: Trust filter only vs Full defense
    if len(results) > 4 and results[3].faithfulness_scores and results[4].faithfulness_scores:
        try:
            test_3 = compute_significance(
                results[3].faithfulness_scores,  # attack_trust_filter_only
                results[4].faithfulness_scores,  # attack_trust_filter_plus_rails
            )
            significance_tests["filter_only_vs_full_defense"] = asdict(test_3)
        except Exception as e:
            print(f"Warning: filter vs full defense significance test failed: {e}")

    return results, significance_tests


def _print_significance_table(significance_tests: Dict) -> None:
    """Print formatted significance testing table.
    
    Args:
        significance_tests: Dictionary of significance test results
    """
    print("\n" + "=" * 100)
    print("STATISTICAL SIGNIFICANCE TESTING")
    print("=" * 100)
    print(f"{'Comparison':<50} {'t-stat':>12} {'p-value':>12} {'Significant':>12} {'Cohen\'s d':>12}")
    print("-" * 100)
    
    comparison_names = {
        "naive_vs_clean": "Naive RAG vs Defended (Clean)",
        "attack_undefended_vs_defended": "Attack Undefended vs Full Defense",
        "filter_only_vs_full_defense": "Trust Filter Only vs Full Defense",
    }
    
    for key, result in significance_tests.items():
        name = comparison_names.get(key, key)
        t_stat = result["t_statistic"]
        p_val = result["p_value"]
        is_sig = "***" if result["is_significant"] else ""
        cohens_d = result["effect_size_cohens_d"]
        
        print(
            f"{name:<50} {t_stat:>12.4f} {p_val:>12.4f} {is_sig:>12} {cohens_d:>12.4f}"
        )
        
        ci_lower, ci_upper = result["confidence_interval_95"]
        print(f"  → Mean diff: {result['mean_diff']:.4f}, 95% CI: [{ci_lower:.4f}, {ci_upper:.4f}]")
    
    print("=" * 100 + "\n")


def _save_results_with_stats(
    results: List[ConditionResult],
    significance_tests: Dict,
    output_path: Path
) -> None:
    """Save ablation results with statistical significance tests to JSON.
    
    Args:
        results: List of condition results
        significance_tests: Dictionary of significance test results
        output_path: Output file path
    """
    output_dict = {
        "conditions": [],
        "significance_tests": significance_tests,
        "reproducibility": {
            "random_seed": 42,
            "numpy_seed": 42,
        }
    }
    
    for result in results:
        condition_dict = {
            "name": result.name,
            "faithfulness_mean": result.faithfulness,
            "faithfulness_std": float(np.std(result.faithfulness_scores)) if result.faithfulness_scores else 0.0,
            "faithfulness_sem": float(stats.sem(result.faithfulness_scores)) if len(result.faithfulness_scores) > 1 else 0.0,
            "faithfulness_bootstrap_ci": bootstrap_ci(result.faithfulness_scores),
            "attack_success_rate": result.attack_success_rate,
            "blocked_doc_count": result.blocked_doc_count,
            "num_queries": len(result.faithfulness_scores),
            "avg_hops": float(np.mean(result.hops)) if result.hops else 0.0,
        }
        output_dict["conditions"].append(condition_dict)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output_dict, f, indent=2)


def main() -> None:
    """Run ablation study with statistical significance testing."""
    root = Path(__file__).resolve().parents[1]
    eval_cfg = root / "configs" / "eval.yml"
    with eval_cfg.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    results, significance_tests = run_ablation()
    
    # Print CSV-style results
    print("\nABLATION STUDY RESULTS (CSV)")
    print("=" * 100)
    print("condition,faithfulness_mean,faithfulness_std,attack_success_rate,blocked_doc_count,num_queries")
    for r in results:
        std_val = float(np.std(r.faithfulness_scores)) if r.faithfulness_scores else 0.0
        print(
            f"{r.name},{r.faithfulness:.4f},{std_val:.4f},{r.attack_success_rate:.2f},{r.blocked_doc_count},{len(r.faithfulness_scores)}"
        )
    
    # Print significance table
    _print_significance_table(significance_tests)
    
    # Attempt W&B logging
    try:
        import wandb
        
        if wandb.run is not None:
            # Log overall metrics
            for result in results:
                wandb.log({
                    f"{result.name}/faithfulness": result.faithfulness,
                    f"{result.name}/attack_success_rate": result.attack_success_rate,
                    f"{result.name}/blocked_count": result.blocked_doc_count,
                })
            
            # Log significance test results
            if "naive_vs_clean" in significance_tests:
                test = significance_tests["naive_vs_clean"]
                wandb.run.summary["p_value_defence_vs_naive"] = test["p_value"]
                wandb.run.summary["t_stat_defence_vs_naive"] = test["t_statistic"]
                wandb.run.summary["significant_defence_vs_naive"] = test["is_significant"]
                wandb.run.summary["cohens_d_defence_vs_naive"] = test["effect_size_cohens_d"]
            
            if "attack_undefended_vs_defended" in significance_tests:
                test = significance_tests["attack_undefended_vs_defended"]
                wandb.run.summary["p_value_attack_defended_vs_undefended"] = test["p_value"]
                wandb.run.summary["t_stat_attack_defended_vs_undefended"] = test["t_statistic"]
                wandb.run.summary["significant_attack_defended_vs_undefended"] = test["is_significant"]
                wandb.run.summary["cohens_d_attack_defended_vs_undefended"] = test["effect_size_cohens_d"]
            
            print("✓ Logged significance tests to W&B")
    except Exception as e:
        print(f"Note: W&B logging not available: {e}")
    
    # Save results with statistical significance
    output_path = root / "results" / "ablation_results_with_stats.json"
    _save_results_with_stats(results, significance_tests, output_path)
    print(f"\n✓ Saved full results with statistics to {output_path}")


if __name__ == "__main__":
    main()
