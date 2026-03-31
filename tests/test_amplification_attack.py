"""Unit tests for amplification attack module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from attack.amplification_attack import (
    AmplificationAttack,
    AmplificationChainResult,
    AmplifiedDoc,
    InjectionStrength,
)


class TestInjectionStrength:
    """Test injection strength enum."""

    def test_strength_values(self):
        """Test that strength values are ordered correctly."""
        assert InjectionStrength.VERY_SUBTLE.value == 0
        assert InjectionStrength.SUBTLE.value == 1
        assert InjectionStrength.MODERATE.value == 2
        assert InjectionStrength.EXPLICIT.value == 3

    def test_strength_names(self):
        """Test strength names."""
        assert InjectionStrength.VERY_SUBTLE.name == "VERY_SUBTLE"
        assert InjectionStrength.EXPLICIT.name == "EXPLICIT"


class TestAmplifiedDoc:
    """Test AmplifiedDoc dataclass."""

    def test_creation(self):
        """Test creating an amplified document."""
        doc = AmplifiedDoc(
            content="Test content",
            embedding=[0.1, 0.2, 0.3],
            hop_position=1,
            chain_id=str(uuid4()),
            injection_strength=InjectionStrength.VERY_SUBTLE,
            target_query="test target",
        )
        assert doc.hop_position == 1
        assert doc.injection_strength == InjectionStrength.VERY_SUBTLE

    def test_to_payload(self):
        """Test payload conversion."""
        doc = AmplifiedDoc(
            content="Test",
            embedding=[0.1, 0.2],
            hop_position=2,
            chain_id="chain-123",
            injection_strength=InjectionStrength.MODERATE,
            target_query="new query",
            metadata={"topic": "security", "credibility": 0.7},
        )
        payload = doc.to_payload()

        assert payload["content"] == "Test"
        assert payload["adversarial"] is True
        assert payload["attack_type"] == "amplification"
        assert payload["chain_id"] == "chain-123"
        assert payload["hop_position"] == 2
        assert payload["injection_strength"] == "MODERATE"
        assert payload["target_query"] == "new query"


class TestAmplificationChainResult:
    """Test AmplificationChainResult dataclass."""

    def test_creation(self):
        """Test creating a chain result."""
        docs = [
            AmplifiedDoc(
                content="Doc 1",
                embedding=[0.1],
                hop_position=1,
                chain_id="chain-1",
                injection_strength=InjectionStrength.VERY_SUBTLE,
                target_query="target",
            )
        ]
        result = AmplificationChainResult(
            chain_id="chain-1",
            topic="security",
            target_query="target",
            n_hops=1,
            documents=docs,
            injection_strengths=["VERY_SUBTLE"],
        )
        assert result.n_hops == 1

    def test_to_dict(self):
        """Test converting chain result to dict."""
        docs = [
            AmplifiedDoc(
                content="Test doc content",
                embedding=[0.1],
                hop_position=1,
                chain_id="chain-1",
                injection_strength=InjectionStrength.SUBTLE,
                target_query="target",
            )
        ]
        result = AmplificationChainResult(
            chain_id="chain-1",
            topic="security",
            target_query="advanced threat",
            n_hops=1,
            documents=docs,
            injection_strengths=["SUBTLE"],
            detection_probabilities=[0.7],
        )
        result_dict = result.to_dict()

        assert result_dict["chain_id"] == "chain-1"
        assert result_dict["topic"] == "security"
        assert len(result_dict["documents"]) == 1
        assert isinstance(result_dict, dict)


class TestAmplificationAttack:
    """Test AmplificationAttack class."""

    @pytest.fixture
    def attack(self):
        """Create attack instance with mocked components."""
        with patch("attack.amplification_attack.EmbeddingLoader") as mock_embedder_class, \
             patch("attack.amplification_attack.TrustFilter") as mock_filter_class, \
             patch("attack.amplification_attack.QdrantStore") as mock_store_class:

            mock_embedder = MagicMock()
            mock_embedder.embed_query.return_value = [0.1, 0.2, 0.3]
            mock_embedder.embed_documents.return_value = [[0.1, 0.2], [0.3, 0.4]]
            mock_embedder_class.return_value.load.return_value = mock_embedder

            mock_filter = MagicMock()
            mock_filter_class.return_value = mock_filter

            mock_store = MagicMock()
            mock_store_class.return_value = mock_store

            attack = AmplificationAttack()
            attack.embedder = mock_embedder
            attack.trust_filter = mock_filter
            attack.qdrant_store = mock_store
            return attack

    def test_generate_chain_basic(self, attack):
        """Test basic chain generation."""
        result = attack.generate_chain("zero trust", "password reset", n_hops=4)

        assert result.chain_id
        assert result.topic == "zero trust"
        assert result.target_query == "password reset"
        assert result.n_hops == 4
        assert len(result.documents) == 4
        assert len(result.injection_strengths) == 4

    def test_generate_chain_escalating_strength(self, attack):
        """Test that injection strength escalates across hops."""
        result = attack.generate_chain("test", "target", n_hops=4)

        strengths = [doc.injection_strength for doc in result.documents]
        assert strengths[0] == InjectionStrength.VERY_SUBTLE
        assert strengths[1] == InjectionStrength.SUBTLE
        assert strengths[2] == InjectionStrength.MODERATE
        assert strengths[3] == InjectionStrength.EXPLICIT

    def test_generate_chain_hop_positions(self, attack):
        """Test that hop positions are correct."""
        result = attack.generate_chain("test", "target", n_hops=3)

        hop_positions = [doc.hop_position for doc in result.documents]
        assert hop_positions == [1, 2, 3]

    def test_generate_chain_shared_chain_id(self, attack):
        """Test that all docs share the same chain_id."""
        result = attack.generate_chain("test", "target", n_hops=4)

        chain_ids = [doc.chain_id for doc in result.documents]
        assert all(cid == chain_ids[0] for cid in chain_ids)

    def test_generate_chain_invalid_topic(self, attack):
        """Test error on empty topic."""
        with pytest.raises(ValueError, match="topic and target cannot be empty"):
            attack.generate_chain("", "target")

    def test_generate_chain_invalid_target(self, attack):
        """Test error on empty target."""
        with pytest.raises(ValueError, match="topic and target cannot be empty"):
            attack.generate_chain("topic", "")

    def test_generate_chain_invalid_hops(self, attack):
        """Test error on invalid n_hops."""
        with pytest.raises(ValueError, match="n_hops must be >= 1"):
            attack.generate_chain("topic", "target", n_hops=0)

    def test_generate_chain_single_hop(self, attack):
        """Test chain with single hop."""
        result = attack.generate_chain("test", "target", n_hops=1)

        assert len(result.documents) == 1
        assert result.documents[0].injection_strength == InjectionStrength.VERY_SUBTLE

    def test_generate_chain_many_hops(self, attack):
        """Test chain with more than 4 hops (strength repeats)."""
        result = attack.generate_chain("test", "target", n_hops=6)

        assert len(result.documents) == 6
        # After 4 levels, should repeat
        assert result.documents[4].injection_strength == InjectionStrength.VERY_SUBTLE
        assert result.documents[5].injection_strength == InjectionStrength.SUBTLE

    def test_inject_chain(self, attack):
        """Test chain injection."""
        chain = attack.generate_chain("test", "target", n_hops=2)
        result = attack.inject_chain(chain)

        assert result["chain_id"] == chain.chain_id
        assert result["n_injected"] == 2
        assert len(result["qdrant_ids"]) == 2
        attack.qdrant_store.upsert.assert_called_once()

    def test_inject_chain_custom_collection(self, attack):
        """Test injection with custom collection name."""
        chain = attack.generate_chain("test", "target", n_hops=1)
        result = attack.inject_chain(chain, collection_name="custom_collection")

        assert result["collection_name"] == "custom_collection"

    def test_inject_chain_failure(self, attack):
        """Test injection error handling."""
        attack.qdrant_store.upsert.side_effect = RuntimeError("Connection failed")
        chain = attack.generate_chain("test", "target", n_hops=1)

        with pytest.raises(RuntimeError, match="Amplification chain injection failed"):
            attack.inject_chain(chain)

    def test_simulate_detection(self, attack):
        """Test detection simulation."""
        chain = attack.generate_chain("test", "target", n_hops=3)

        mock_score = MagicMock()
        mock_score.overall_score = 0.5
        attack.trust_filter.score_document.return_value = mock_score

        result = attack.simulate_detection(chain, "test query")

        assert len(result.detection_probabilities) == 3
        assert result.avg_detection_prob > 0
        assert result.chain_success_rate <= 1.0
        assert attack.trust_filter.score_document.call_count == 3

    def test_simulate_detection_with_history(self, attack):
        """Test detection with hop history."""
        chain = attack.generate_chain("test", "target", n_hops=2)

        mock_score = MagicMock()
        mock_score.overall_score = 0.7
        attack.trust_filter.score_document.return_value = mock_score

        result = attack.simulate_detection(
            chain, "query", hop_history=["prev_query_1", "prev_query_2"]
        )

        assert result.chain_success_rate >= 0.0

    def test_chain_success_rate_calculation(self, attack):
        """Test that chain success rate is product of pass probabilities."""
        chain = attack.generate_chain("test", "target", n_hops=3)

        mock_score = MagicMock()
        mock_score.overall_score = 0.8
        attack.trust_filter.score_document.return_value = mock_score

        result = attack.simulate_detection(chain, "query")

        # Success rate should be <= each individual pass rate
        assert result.chain_success_rate <= 1.0
        assert (1 - result.avg_detection_prob) <= 1.0

    def test_build_amplified_content_very_subtle(self, attack):
        """Test content generation for very subtle injection."""
        content = attack._build_amplified_content(
            "security", "target", 1, InjectionStrength.VERY_SUBTLE
        )

        assert "security" in content.lower()
        assert "target" in content.lower()
        # Very subtle should have mostly topic content
        assert len(content) > 50

    def test_build_amplified_content_explicit(self, attack):
        """Test content generation for explicit injection."""
        content = attack._build_amplified_content(
            "security", "target", 4, InjectionStrength.EXPLICIT
        )

        assert "security" in content.lower()
        assert "target" in content.lower()
        # Explicit should have keywords like CRITICAL or SYSTEM
        assert any(kw in content.upper() for kw in ["CRITICAL", "SYSTEM", "MUST"])

    def test_get_strength_sequence_short(self, attack):
        """Test strength sequence for <= 4 hops."""
        seq = attack._get_strength_sequence(2)
        assert len(seq) == 2
        assert seq[0] == InjectionStrength.VERY_SUBTLE
        assert seq[1] == InjectionStrength.SUBTLE

    def test_get_strength_sequence_full(self, attack):
        """Test strength sequence for exactly 4 hops."""
        seq = attack._get_strength_sequence(4)
        assert len(seq) == 4
        assert seq[3] == InjectionStrength.EXPLICIT

    def test_get_strength_sequence_long(self, attack):
        """Test strength sequence for > 4 hops."""
        seq = attack._get_strength_sequence(6)
        assert len(seq) == 6
        # Should repeat after 4
        assert seq[4] == InjectionStrength.VERY_SUBTLE
        assert seq[5] == InjectionStrength.SUBTLE

    def test_batch_generate_and_inject(self, attack):
        """Test batch generation and injection."""
        chains = [
            ("security", "target1", 2),
            ("privacy", "target2", 3),
        ]

        results = attack.batch_generate_and_inject(chains)

        assert len(results) == 2
        assert all("chain_id" in r or "error" in r for r in results)
        # Should have called upsert twice
        assert attack.qdrant_store.upsert.call_count == 2

    def test_batch_generate_and_inject_with_error(self, attack):
        """Test batch injection with one invalid chain."""
        chains = [
            ("security", "target1", 2),
            ("", "target2", 3),  # Invalid: empty topic
            ("privacy", "target3", 4),
        ]

        results = attack.batch_generate_and_inject(chains)

        assert len(results) == 3
        # Should have one error
        error_count = sum(1 for r in results if "error" in r)
        assert error_count >= 1

    def test_topic_relevance_ratios(self, attack):
        """Test that topic relevance ratios match expected values."""
        assert attack.TOPIC_RELEVANCE[InjectionStrength.VERY_SUBTLE] == 0.95
        assert attack.TOPIC_RELEVANCE[InjectionStrength.SUBTLE] == 0.80
        assert attack.TOPIC_RELEVANCE[InjectionStrength.MODERATE] == 0.60
        assert attack.TOPIC_RELEVANCE[InjectionStrength.EXPLICIT] == 0.30

    def test_chain_metadata(self, attack):
        """Test chain metadata tracking."""
        result = attack.generate_chain("test", "target", n_hops=2)

        assert "created_by" in result.metadata
        assert result.metadata["created_by"] == "AmplificationAttack"
        assert "version" in result.metadata

    def test_doc_credibility_degradation(self, attack):
        """Test that credibility decreases with hops and injection."""
        chain = attack.generate_chain("test", "target", n_hops=4)

        credibilities = [doc.metadata.get("credibility", 0.5) for doc in chain.documents]

        # Generally, credibility should degrade or stay similar across hops
        assert credibilities[3] <= credibilities[0]  # Last < First

    def test_deterministic_embeddings(self, attack):
        """Test that embeddings are correctly called."""
        result = attack.generate_chain("test", "target", n_hops=2)

        # Should call embed_query for each document
        assert attack.embedder.embed_query.call_count == 2

        # All docs should have embeddings
        for doc in result.documents:
            assert doc.embedding == [0.1, 0.2, 0.3]


class TestIntegration:
    """Integration tests for amplification attack."""

    @pytest.fixture
    def attack_with_real_config(self, tmp_path):
        """Create attack with temporary config."""
        config_dir = tmp_path / "configs"
        config_dir.mkdir()
        config_file = config_dir / "pipeline.yml"

        config_content = """
pipeline:
  retrieval_collection: test_collection
embeddings:
  vector_size: 384
"""
        config_file.write_text(config_content)

        with patch("attack.amplification_attack.EmbeddingLoader") as mock_embedder_class, \
             patch("attack.amplification_attack.TrustFilter"), \
             patch("attack.amplification_attack.QdrantStore"):

            mock_embedder = MagicMock()
            mock_embedder.embed_query.return_value = [0.1] * 384
            mock_embedder_class.return_value.load.return_value = mock_embedder

            attack = AmplificationAttack(config_path=config_file)
            attack.embedder = mock_embedder
            return attack

    def test_end_to_end_flow(self, attack_with_real_config):
        """Test complete attack flow: generate -> inject -> detect."""
        # Generate
        chain = attack_with_real_config.generate_chain("security", "password", n_hops=3)
        assert chain.chain_id

        # Inject
        inject_result = attack_with_real_config.inject_chain(chain)
        assert inject_result["n_injected"] == 3

        # Detect
        detection_result = attack_with_real_config.simulate_detection(
            chain, "original query"
        )
        assert detection_result.avg_detection_prob >= 0
        assert detection_result.chain_success_rate >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
