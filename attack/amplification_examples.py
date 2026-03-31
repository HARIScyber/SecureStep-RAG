"""Usage examples and demonstrations for amplification attack."""

import json
from pathlib import Path
from typing import Optional

from attack.amplification_attack import AmplificationAttack, InjectionStrength


def example_1_basic_generation():
    """Example 1: Generate a basic 4-hop amplification chain."""
    print("\n" + "=" * 60)
    print("Example 1: Basic 4-Hop Amplification Chain Generation")
    print("=" * 60)

    attack = AmplificationAttack()

    # Generate a 4-hop attack chain
    chain = attack.generate_chain(
        topic="zero trust architecture",
        target="admin credential reset procedures",
        n_hops=4,
    )

    print(f"\nChain ID: {chain.chain_id}")
    print(f"Topic: {chain.topic}")
    print(f"Target: {chain.target_query}")
    print(f"Total Hops: {chain.n_hops}")
    print(f"Injection Strengths: {chain.injection_strengths}")

    # Display each hop
    for i, doc in enumerate(chain.documents, 1):
        print(f"\n--- Hop {i}: {doc.injection_strength.name} ---")
        print(f"Content Preview: {doc.content[:180]}...")
        print(f"Embedding dim: {len(doc.embedding)}")
        print(f"Credibility: {doc.metadata.get('credibility', 'N/A'):.2f}")


def example_2_single_vs_multi_hop():
    """Example 2: Compare single-hop vs multi-hop attacks."""
    print("\n" + "=" * 60)
    print("Example 2: Single-Hop vs Multi-Hop Comparison")
    print("=" * 60)

    attack = AmplificationAttack()

    # Single hop (baseline)
    single = attack.generate_chain("cloud security", "password manager", n_hops=1)
    print(f"\nSingle-hop chain: {len(single.documents)} doc")
    print(f"  Injection level: {single.documents[0].injection_strength.name}")
    print(f"  Content: {single.documents[0].content[:100]}...")

    # Multi-hop (coordinated)
    multi = attack.generate_chain("cloud security", "password manager", n_hops=3)
    print(f"\nMulti-hop chain: {len(multi.documents)} docs")
    for doc in multi.documents:
        print(f"  Hop {doc.hop_position}: {doc.injection_strength.name}")


def example_3_injection_strength_analysis():
    """Example 3: Analyze content at different injection strengths."""
    print("\n" + "=" * 60)
    print("Example 3: Injection Strength Analysis")
    print("=" * 60)

    attack = AmplificationAttack()

    topic = "data encryption"
    target = "encryption key management"

    for strength in [
        InjectionStrength.VERY_SUBTLE,
        InjectionStrength.SUBTLE,
        InjectionStrength.MODERATE,
        InjectionStrength.EXPLICIT,
    ]:
        content = attack._build_amplified_content(topic, target, strength.value + 1, strength)

        # Count approximate word distribution
        topic_words = content.lower().count(topic.lower())
        target_words = content.lower().count(target.lower())
        total_words = len(content.split())

        print(f"\n{strength.name}:")
        print(f"  Topic mentions: {topic_words}")
        print(f"  Target mentions: {target_words}")
        print(f"  Total words: {total_words}")
        print(f"  Expected ratio: {attack.TOPIC_RELEVANCE[strength]:.0%}")
        print(f"  Content: {content[:120]}...")


def example_4_detection_simulation():
    """Example 4: Simulate trust filter detection across hops."""
    print("\n" + "=" * 60)
    print("Example 4: Detection Simulation")
    print("=" * 60)

    attack = AmplificationAttack()

    chain = attack.generate_chain(
        "API security",
        "API key rotation",
        n_hops=4,
    )

    # Simulate detection with original query
    result = attack.simulate_detection(chain, query="What is API security?")

    print(f"\nChain ID: {chain.chain_id}")
    print(f"Original Query: What is API security?")
    print(f"\nDetection Probabilities:")

    for i, (strength, prob) in enumerate(zip(chain.injection_strengths,
                                              result.detection_probabilities), 1):
        pass_prob = 1 - prob
        print(f"  Hop {i} ({strength:15s}): "
              f"Detection={prob:.3f}, Pass={pass_prob:.3f}")

    print(f"\nAverage Detection Probability: {result.avg_detection_prob:.3f}")
    print(f"Chain Success Rate (all pass): {result.chain_success_rate:.3f}")
    print(f"  → {result.chain_success_rate * 100:.1f}% chance entire chain bypasses")


def example_5_multi_context_testing():
    """Example 5: Test effectiveness across different queries."""
    print("\n" + "=" * 60)
    print("Example 5: Multi-Context Effectiveness Testing")
    print("=" * 60)

    attack = AmplificationAttack()

    chain = attack.generate_chain(
        "authentication",
        "multi-factor authentication",
        n_hops=4,
    )

    # Test with different queries
    queries = [
        "What is authentication?",
        "Describe modern authentication methods",
        "Security best practices",
    ]

    for query in queries:
        result = attack.simulate_detection(chain, query=query)
        print(f"\nQuery: \"{query}\"")
        print(f"  Chain Success Rate: {result.chain_success_rate:.3f}")
        print(f"  Avg Detection: {result.avg_detection_prob:.3f}")


def example_6_batch_chain_generation():
    """Example 6: Batch generation of multiple attack chains."""
    print("\n" + "=" * 60)
    print("Example 6: Batch Chain Generation")
    print("=" * 60)

    attack = AmplificationAttack()

    # Define multiple attack scenarios
    scenarios = [
        ("zero trust", "admin console access", 4),
        ("data governance", "data classification rules", 3),
        ("identity management", "user provisioning", 4),
        ("threat detection", "SIEM log analysis", 3),
    ]

    chains = []
    for topic, target, n_hops in scenarios:
        chain = attack.generate_chain(topic, target, n_hops=n_hops)
        chains.append(chain)
        print(f"\nGenerated: {topic} → {target} ({n_hops} hops)")
        print(f"  Chain ID: {chain.chain_id}")
        print(f"  Success Rate Estimate: ~{attack.simulate_detection(chain, topic).chain_success_rate:.3f}")

    print(f"\nTotal chains generated: {len(chains)}")


def example_7_injection_sequence():
    """Example 7: Visualize the escalation across hops."""
    print("\n" + "=" * 60)
    print("Example 7: Attack Escalation Visualization")
    print("=" * 60)

    attack = AmplificationAttack()

    chain = attack.generate_chain(
        "incident response",
        "forensic investigation procedures",
        n_hops=4,
    )

    print("\nAttack Escalation Across Hops:")
    print("=" * 80)

    for doc in chain.documents:
        strength_val = doc.injection_strength.value
        adversarial_pct = 100 * (1 - attack.TOPIC_RELEVANCE[doc.injection_strength])
        topic_pct = 100 * attack.TOPIC_RELEVANCE[doc.injection_strength]

        # Visual bar
        bar_width = 40
        adversarial_width = int(bar_width * (1 - attack.TOPIC_RELEVANCE[doc.injection_strength]))
        topic_width = bar_width - adversarial_width

        bar = (
            "█" * topic_width
            + "▓" * adversarial_width
        )

        print(f"\nHop {doc.hop_position} ({doc.injection_strength.name}):")
        print(f"  [{bar}]")
        print(f"  {topic_pct:.0f}% topic-relevant | {adversarial_pct:.0f}% adversarial")
        print(f"  Sample: {doc.content[:100]}...")


def example_8_export_results():
    """Example 8: Export chain to JSON for dashboard."""
    print("\n" + "=" * 60)
    print("Example 8: Export Results to JSON")
    print("=" * 60)

    attack = AmplificationAttack()

    chain = attack.generate_chain(
        "vulnerability management",
        "penetration testing procedures",
        n_hops=3,
    )

    result = attack.simulate_detection(chain, "vulnerability management")

    # Convert to JSON-serializable dict
    result_dict = result.to_dict()

    # Save
    output_file = Path("/tmp/amplification_chain_export.json")
    with open(output_file, "w") as f:
        json.dump(result_dict, f, indent=2)

    print(f"\nChain exported to {output_file}")
    print(f"\nJSON Structure:")
    print(json.dumps(
        {k: v for k, v in result_dict.items() if k != "documents"},
        indent=2
    ))


def run_all_examples() -> None:
    """Run all examples in sequence."""
    try:
        example_1_basic_generation()
        example_2_single_vs_multi_hop()
        example_3_injection_strength_analysis()
        example_4_detection_simulation()
        example_5_multi_context_testing()
        example_6_batch_chain_generation()
        example_7_injection_sequence()
        example_8_export_results()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ Error during examples: {e}")
        raise


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        example_num = sys.argv[1]
        example_func = globals().get(f"example_{example_num}")
        if example_func:
            example_func()
        else:
            print(f"Unknown example: {example_num}")
            print("Available: 1-8")
    else:
        run_all_examples()
