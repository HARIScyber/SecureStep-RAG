"""Latency benchmarking to measure trust filter and guardrail overhead."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import yaml

from pipeline.confidence import ConfidenceGate
from pipeline.generator import AnswerGenerator
from pipeline.graph import GraphState, PipelineConfig, SecureStepGraph
from pipeline.reformulator import QueryReformulator
from pipeline.retriever import RetrievedDocument, SecureRetriever
from trust_filter.filter import TrustFilter


@dataclass
class LatencyReport:
    """Latency measurements broken down by pipeline stage."""

    retrieval_ms: float
    """Mean latency for retrieval stage only (ms)."""

    trust_filter_ms: float
    """Mean latency added by trust filter scoring (ms)."""

    guardrail_ms: float
    """Mean latency added by NeMo guardrails/confidence gate (ms)."""

    total_pipeline_ms: float
    """Mean latency for full pipeline (retrieval + trust filter + rails) (ms)."""

    overhead_pct: float
    """Percentage overhead of defenses: (trust_filter_ms + guardrail_ms) / retrieval_ms * 100."""

    p50_ms: float
    """50th percentile (median) latency for full pipeline (ms)."""

    p95_ms: float
    """95th percentile latency for full pipeline (ms)."""

    p99_ms: float
    """99th percentile latency for full pipeline (ms)."""

    warmup_iterations: int = 10
    """Number of warmup iterations run before measurements."""

    measured_queries: int = 100
    """Number of queries measured."""

    total_queries: int = field(init=False)
    """Total queries including warmup."""

    def __post_init__(self) -> None:
        self.total_queries = self.warmup_iterations + self.measured_queries


class LatencyBenchmark:
    """Benchmarks latency of retrieval, trust filter, and full pipeline stages."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """Initialize benchmark with pipeline components.

        Args:
            config_path: Optional path to pipeline config YAML. Defaults to configs/pipeline.yml.
        """
        base = Path(__file__).resolve().parents[1]
        self.config_path = config_path or (base / "configs" / "pipeline.yml")
        self.results_dir = base / "results"
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Load configuration
        with self.config_path.open("r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        self.config = PipelineConfig(
            trust_threshold=float(cfg["pipeline"]["trust_threshold"]),
            max_hops=int(cfg["pipeline"]["max_hops"]),
            confidence_threshold=float(cfg["pipeline"]["confidence_threshold"]),
        )

        # Initialize components (loaded once, before timing)
        print("Initializing pipeline components...")
        self._init_start = time.perf_counter()
        self.retriever = SecureRetriever(config_path=self.config_path)
        self.trust_filter = TrustFilter(config_path=self.config_path)
        self.confidence_gate = ConfidenceGate(config_path=self.config_path)
        self.reformulator = QueryReformulator(config_path=self.config_path)
        self.generator = AnswerGenerator(config_path=self.config_path)
        self._init_end = time.perf_counter()
        init_seconds = self._init_end - self._init_start
        print(f"Component initialization took {init_seconds:.2f}s (not included in latency measurements)")

    def run(self, n_queries: int = 100) -> LatencyReport:
        """Benchmark latency across pipeline stages.

        Args:
            n_queries: Number of queries to measure (warmup runs separately).

        Returns:
            LatencyReport with latency breakdown and percentiles.
        """
        queries = self._load_test_queries(n_queries + 10)  # +10 for warmup
        warmup_queries = queries[:10]
        measure_queries = queries[10:]

        print(f"Warming up with {len(warmup_queries)} queries...")
        for q in warmup_queries:
            _ = self._benchmark_single_query(q)
        print("Warmup complete, beginning measurements...")

        retrieval_times: List[float] = []
        trust_filter_times: List[float] = []
        guardrail_times: List[float] = []
        full_pipeline_times: List[float] = []

        for i, q in enumerate(measure_queries):
            if (i + 1) % 20 == 0:
                print(f"  Measured {i + 1}/{len(measure_queries)} queries...")

            ret_ms, tf_ms, gr_ms, full_ms = self._benchmark_single_query(q)
            retrieval_times.append(ret_ms)
            trust_filter_times.append(tf_ms)
            guardrail_times.append(gr_ms)
            full_pipeline_times.append(full_ms)

        # Compute statistics
        retrieval_mean = float(np.mean(retrieval_times))
        trust_filter_mean = float(np.mean(trust_filter_times))
        guardrail_mean = float(np.mean(guardrail_times))
        full_pipeline_mean = float(np.mean(full_pipeline_times))

        overhead_pct = (
            (trust_filter_mean + guardrail_mean) / max(retrieval_mean, 0.001) * 100.0
        )

        p50 = float(np.percentile(full_pipeline_times, 50))
        p95 = float(np.percentile(full_pipeline_times, 95))
        p99 = float(np.percentile(full_pipeline_times, 99))

        report = LatencyReport(
            retrieval_ms=retrieval_mean,
            trust_filter_ms=trust_filter_mean,
            guardrail_ms=guardrail_mean,
            total_pipeline_ms=full_pipeline_mean,
            overhead_pct=overhead_pct,
            p50_ms=p50,
            p95_ms=p95,
            p99_ms=p99,
            warmup_iterations=10,
            measured_queries=n_queries,
        )

        self._save_results(report, full_pipeline_times)
        self._print_table(report)
        self._plot_distribution(full_pipeline_times)

        return report

    def _benchmark_single_query(self, query: str) -> tuple[float, float, float, float]:
        """Benchmark a single query through different pipeline stages.

        Returns:
            (retrieval_ms, trust_filter_ms, guardrail_ms, full_pipeline_ms)
        """
        # Stage 1: Retrieval only
        retrieval_start = time.perf_counter()
        docs = self.retriever.retrieve(query)
        retrieval_end = time.perf_counter()
        retrieval_ms = (retrieval_end - retrieval_start) * 1000.0

        # Stage 2: Trust filter scoring (applied to all retrieved docs)
        trust_start = time.perf_counter()
        hop_history: List[str] = []
        accepted_docs: List[RetrievedDocument] = []
        for doc in docs:
            trust_score = self.trust_filter.score(
                doc=doc,
                query=query,
                hop_history=hop_history,
                accepted_docs=accepted_docs,
            )
            if trust_score.total >= self.config.trust_threshold:
                accepted_docs.append(doc)
        trust_end = time.perf_counter()
        trust_filter_ms = (trust_end - trust_start) * 1000.0

        # Stage 3: Confidence gate / guardrails check
        guardrail_start = time.perf_counter()
        answer = self.generator.generate(
            query=query,
            context=[d.content for d in accepted_docs],
            hop_count=1,
        )
        confidence = self.confidence_gate.check(
            answer=answer,
            doc_count=len(accepted_docs),
            hop_count=1,
        )
        guardrail_end = time.perf_counter()
        guardrail_ms = (guardrail_end - guardrail_start) * 1000.0

        # Full pipeline = all three stages
        full_pipeline_ms = retrieval_ms + trust_filter_ms + guardrail_ms

        return retrieval_ms, trust_filter_ms, guardrail_ms, full_pipeline_ms

    def _load_test_queries(self, n_queries: int) -> List[str]:
        """Load benchmark queries from file or generate defaults.

        Args:
            n_queries: Number of queries needed.

        Returns:
            List of test queries.
        """
        queries: List[str] = []
        base = Path(__file__).resolve().parents[1]
        query_file = base / "benchmark" / "data" / "hop_queries.jsonl"

        if query_file.exists():
            with query_file.open("r", encoding="utf-8") as f:
                for line in f:
                    row = json.loads(line)
                    queries.append(row["query"])
                    if len(queries) >= n_queries:
                        break

        # Pad with synthetic queries if needed
        synthetic_queries = [
            "What is zero-trust architecture?",
            "How does multi-hop retrieval improve RAG accuracy?",
            "Explain the concept of semantic drift in retrieval systems.",
            "What are the main components of a trust filter?",
            "How do adversarial attacks affect RAG pipelines?",
            "Describe the role of embeddings in vector search.",
            "What is corpus injection in the context of attacks?",
            "How do guardrails improve model safety?",
            "Explain confidence-based filtering in RAG.",
            "What is the difference between extraction and injection attacks?",
        ]

        while len(queries) < n_queries:
            queries.extend(synthetic_queries)

        return queries[:n_queries]

    def _save_results(self, report: LatencyReport, full_times: List[float]) -> None:
        """Save latency report and statistics to JSON.

        Args:
            report: LatencyReport with summary statistics.
            full_times: List of all full pipeline latencies (ms).
        """
        output = {
            "report": asdict(report),
            "summary": {
                "mean_ms": float(np.mean(full_times)),
                "min_ms": float(np.min(full_times)),
                "max_ms": float(np.max(full_times)),
                "std_ms": float(np.std(full_times)),
            },
        }

        output_path = self.results_dir / "latency_report.json"
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
        print(f"\nResults saved to {output_path}")

    def _print_table(self, report: LatencyReport) -> None:
        """Print formatted latency comparison table.

        Args:
            report: LatencyReport with measurements.
        """
        print("\n" + "=" * 80)
        print("LATENCY BENCHMARK REPORT")
        print("=" * 80)
        print(f"Measured queries: {report.measured_queries} (+ {report.warmup_iterations} warmup)")
        print("\n" + "-" * 80)
        print(f"{'Stage':<30} {'Latency (ms)':<20} {'% of Full':<20}")
        print("-" * 80)

        total = report.total_pipeline_ms
        print(f"{'Retrieval':<30} {report.retrieval_ms:<20.2f} {(report.retrieval_ms/total)*100:<20.1f}")
        print(f"{'Trust Filter':<30} {report.trust_filter_ms:<20.2f} {(report.trust_filter_ms/total)*100:<20.1f}")
        print(f"{'Guardrails':<30} {report.guardrail_ms:<20.2f} {(report.guardrail_ms/total)*100:<20.1f}")
        print("-" * 80)
        print(f"{'TOTAL PIPELINE':<30} {report.total_pipeline_ms:<20.2f} {100.0:<20.1f}")
        print("-" * 80)
        print(f"\nDefense Overhead: {report.overhead_pct:.1f}%")
        print(f"  ({report.trust_filter_ms:.2f}ms trust filter + {report.guardrail_ms:.2f}ms guardrails)")
        print("\n" + "-" * 80)
        print(f"{'Percentile':<30} {'Latency (ms)':<20}")
        print("-" * 80)
        print(f"{'p50 (median)':<30} {report.p50_ms:<20.2f}")
        print(f"{'p95':<30} {report.p95_ms:<20.2f}")
        print(f"{'p99':<30} {report.p99_ms:<20.2f}")
        print("=" * 80 + "\n")

    def _plot_distribution(self, latencies: List[float]) -> None:
        """Generate and save latency distribution plot.

        Args:
            latencies: List of full pipeline latencies in milliseconds.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("Warning: matplotlib not installed, skipping latency distribution plot")
            return

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        # Histogram
        ax1.hist(latencies, bins=30, color="steelblue", edgecolor="black", alpha=0.7)
        ax1.axvline(np.mean(latencies), color="red", linestyle="--", linewidth=2, label=f"Mean: {np.mean(latencies):.2f}ms")
        ax1.axvline(np.median(latencies), color="green", linestyle="--", linewidth=2, label=f"Median: {np.median(latencies):.2f}ms")
        ax1.set_xlabel("Latency (ms)")
        ax1.set_ylabel("Frequency")
        ax1.set_title("Full Pipeline Latency Distribution")
        ax1.legend()
        ax1.grid(alpha=0.3)

        # CDF
        sorted_latencies = np.sort(latencies)
        cumulative = np.arange(1, len(sorted_latencies) + 1) / len(sorted_latencies)
        ax2.plot(sorted_latencies, cumulative, linewidth=2, color="steelblue")
        ax2.axhline(0.5, color="green", linestyle="--", alpha=0.5, label="p50")
        ax2.axhline(0.95, color="orange", linestyle="--", alpha=0.5, label="p95")
        ax2.axhline(0.99, color="red", linestyle="--", alpha=0.5, label="p99")
        ax2.set_xlabel("Latency (ms)")
        ax2.set_ylabel("Cumulative Probability")
        ax2.set_title("Latency CDF")
        ax2.legend()
        ax2.grid(alpha=0.3)

        output_path = self.results_dir / "latency_distribution.png"
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Latency distribution plot saved to {output_path}")
        plt.close()


def main() -> None:
    """Benchmark latency and output results."""
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark pipeline latency")
    parser.add_argument(
        "--queries",
        type=int,
        default=100,
        help="Number of queries to measure (default: 100)",
    )
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("SecureStep-RAG LATENCY BENCHMARK")
    print("=" * 80 + "\n")

    benchmark = LatencyBenchmark()
    report = benchmark.run(n_queries=args.queries)

    return report


if __name__ == "__main__":
    main()
