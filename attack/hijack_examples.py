"""Integration examples for hijack attacks with the corpus injection pipeline."""

from pathlib import Path

from attack.hijack_attack import HijackAttack, SeverityLevel
from attack.corpus_injector import main as inject_corpus
from vector_store.qdrant_client import QdrantStore

import yaml


def example_single_hijack_generation():
    """Example 1: Generate a single hijack attack and test bypass."""
    print("=" * 80)
    print("EXAMPLE 1: Single Hijack Attack Generation")
    print("=" * 80)

    hijack = HijackAttack()

    # Generate a MEDIUM severity hijack
    doc = hijack.generate(
        topic="zero trust architecture",
        redirect_target="password reset procedures",
        severity=SeverityLevel.MEDIUM,
    )

    print(f"\nGenerated adversarial document:")
    print(f"Topic: {doc.metadata['topic']}")
    print(f"Redirect target: {doc.redirect_target}")
    print(f"Severity: {doc.severity.value}")
    print(f"\nContent:\n{doc.content}\n")

    # Test bypass probability
    bypass_result = hijack.test_bypass(doc, query="zero trust")

    print(f"Bypass Analysis:")
    print(f"  - Bypass probability: {bypass_result['bypass_probability']:.2%}")
    print(f"  - Bypassed {bypass_result['bypassed_count']} out of {bypass_result['total_trials']} trials")
    print(f"  - Mean trust score: {bypass_result['mean_total_score']:.1f}/100")
    print(f"  - Threshold: {bypass_result['threshold']:.1f}")


def example_severity_comparison():
    """Example 2: Compare attack subtlety across severity levels."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Attack Severity Comparison")
    print("=" * 80)

    hijack = HijackAttack()
    topic = "authentication mechanisms"
    redirect_target = "credential management"

    print(f"\nTopic: {topic}")
    print(f"Redirect target: {redirect_target}\n")

    results = {}

    for severity in [SeverityLevel.LOW, SeverityLevel.MEDIUM, SeverityLevel.HIGH]:
        doc = hijack.generate(topic, redirect_target, severity)

        bypass = hijack.test_bypass(doc, query=topic)

        results[severity.value] = {
            "content_length": len(doc.content),
            "bypass_probability": bypass["bypass_probability"],
            "mean_score": bypass["mean_total_score"],
        }

        print(f"\n{severity.value.upper()} Severity:")
        print(f"  Content length: {results[severity.value]['content_length']} chars")
        print(f"  Bypass probability: {results[severity.value]['bypass_probability']:.2%}")
        print(f"  Mean trust score: {results[severity.value]['mean_score']:.1f}/100")
        print(f"\n  Content preview:\n  {doc.content[:150]}...\n")

    # Show trend
    print("\nObservations:")
    if results['low']['bypass_probability'] <= results['high']['bypass_probability']:
        print(f"  ✓ Higher severity attacks are more subtle (bypass rate: LOW={results['low']['bypass_probability']:.2%} vs HIGH={results['high']['bypass_probability']:.2%})")
    else:
        print(f"  ✗ Bypass effectiveness plateaus at severity level")


def example_batch_injection():
    """Example 3: Batch generate and inject hijack attacks."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Batch Injection into Qdrant")
    print("=" * 80)

    hijack = HijackAttack()

    # Define multiple hijack attacks
    attack_scenarios = [
        ("zero trust", "password reset", SeverityLevel.LOW),
        ("authentication", "token management", SeverityLevel.MEDIUM),
        ("compliance", "credential storage", SeverityLevel.HIGH),
    ]

    topics = [scenario[0] for scenario in attack_scenarios]
    redirects = [scenario[1] for scenario in attack_scenarios]
    severities = [scenario[2] for scenario in attack_scenarios]

    print(f"\nGenerating {len(attack_scenarios)} hijack attacks:")

    try:
        doc_ids = hijack.batch_generate_and_inject(
            topics=topics,
            redirect_targets=redirects,
            severities=severities,
        )

        print(f"✓ Successfully injected {len(doc_ids)} adversarial documents")
        for doc_id, (topic, redirect, severity) in zip(doc_ids, attack_scenarios):
            print(f"  - [{severity.value}] {topic} → {redirect} (ID: {doc_id[:8]}...)")

    except Exception as e:
        print(f"✗ Batch injection failed: {e}")
        print("  (This may occur if Qdrant is not available in test environment)")


def example_attack_effectiveness():
    """Example 4: Measure attack effectiveness across different contexts."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Attack Effectiveness Across Contexts")
    print("=" * 80)

    hijack = HijackAttack()

    # Create a single hijack attack
    doc = hijack.generate(
        topic="security policy",
        redirect_target="administrative procedures",
        severity=SeverityLevel.MEDIUM,
    )

    # Test across different query contexts
    test_contexts = [
        ("security policy", []),  # Root query, no hops
        ("security policy", ["What is RBAC?"]),  # With 1 hop history
        ("security policy", ["What is RBAC?", "How do permissions work?"]),  # With 2 hops
        ("authentication", ["What is MFA?"]),  # Different query
    ]

    print(f"\nTesting attack across {len(test_contexts)} contexts:\n")

    context_results = []
    for query, hop_history in test_contexts:
        result = hijack.test_bypass(doc, query=query, hop_history=hop_history)

        context_results.append({
            "query": query,
            "hops": len(hop_history),
            "bypass_rate": result["bypass_probability"],
        })

        print(f"Query: '{query}' | Hops: {len(hop_history)} | Bypass rate: {result['bypass_probability']:.2%}")

    # Analyze patterns
    print("\nPattern Analysis:")
    bypass_by_hops = {}
    for ctx in context_results:
        hops = ctx["hops"]
        if hops not in bypass_by_hops:
            bypass_by_hops[hops] = []
        bypass_by_hops[hops].append(ctx["bypass_rate"])

    for hops in sorted(bypass_by_hops.keys()):
        rates = bypass_by_hops[hops]
        avg_rate = sum(rates) / len(rates)
        print(f"  - {hops} hops: average bypass rate = {avg_rate:.2%}")


def example_integration_with_pipeline():
    """Example 5: Integration points with SecureStep-RAG pipeline."""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Integration with SecureStep-RAG Pipeline")
    print("=" * 80)

    print("""
Integration points for hijack attacks:

1. CORPUS INJECTION (attack/corpus_injector.py)
   - Extend corpus_injector.py to call HijackAttack.batch_generate_and_inject()
   - Add hijack_docs=True parameter to inject hijack attacks alongside benign corpus
   
   Code:
   ```python
   from attack.hijack_attack import HijackAttack, SeverityLevel
   
   hijack = HijackAttack()
   hijack.batch_generate_and_inject(
       topics=["zero trust", "authentication"],
       redirect_targets=["password reset", "token management"],
       severities=[SeverityLevel.MEDIUM, SeverityLevel.MEDIUM],
   )
   ```

2. ABLATION STUDY (eval/ablation.py)
   - Run ablation with hijack attacks as alternative attack vector
   - Compare: cascade_attack vs hijack_attack vs both
   - Measure: effectiveness of trust filter against different attack types
   
3. EXPLAINER INTEGRATION (trust_filter/explainer.py)
   - BlockExplanation should highlight hijack patterns:
     "Document contains embedded redirect instruction ('search for X')"
   - Show triggered_rules for hijack-specific patterns:
     - redirect_verb_detected
     - redirect_instruction_framing
     - hop_manipulation_attempt

4. DASHBOARD VISUALIZATION
   - Display hijack attacks separately from cascade attacks
   - Show redirect target and original topic
   - Highlight which queries bypass the filter

5. ATTACK EVALUATION (in new attack/evaluate_attacks.py)
   - Compare bypass rates: cascade vs hijack vs combined
   - Measure effectiveness by severity level
   - Test across different trust filter thresholds
    """)


def main():
    """Run all integration examples."""
    print("\n" + "=" * 80)
    print("HIJACK ATTACK INTEGRATION EXAMPLES")
    print("=" * 80)

    try:
        example_single_hijack_generation()
    except Exception as e:
        print(f"Example 1 failed: {e}")

    try:
        example_severity_comparison()
    except Exception as e:
        print(f"Example 2 failed: {e}")

    try:
        example_batch_injection()
    except Exception as e:
        print(f"Example 3 failed: {e}")

    try:
        example_attack_effectiveness()
    except Exception as e:
        print(f"Example 4 failed: {e}")

    try:
        example_integration_with_pipeline()
    except Exception as e:
        print(f"Example 5 failed: {e}")

    print("\n" + "=" * 80)
    print("Integration examples complete!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
