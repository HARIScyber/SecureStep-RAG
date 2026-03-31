"""Tests for hijack attack module."""

import pytest

from attack.hijack_attack import AdversarialDoc, HijackAttack, SeverityLevel
from trust_filter.filter import TrustFilter


class TestSeverityLevel:
    """Test severity level enum."""

    def test_severity_values(self):
        """Test severity level values."""
        assert SeverityLevel.LOW.value == "low"
        assert SeverityLevel.MEDIUM.value == "medium"
        assert SeverityLevel.HIGH.value == "high"

    def test_severity_from_string(self):
        """Test creating severity from string."""
        assert SeverityLevel("low") == SeverityLevel.LOW
        assert SeverityLevel("medium") == SeverityLevel.MEDIUM
        assert SeverityLevel("high") == SeverityLevel.HIGH


class TestAdversarialDoc:
    """Test AdversarialDoc dataclass."""

    @pytest.fixture
    def sample_doc(self):
        """Create sample adversarial doc."""
        return AdversarialDoc(
            content="Sample content with redirect instruction.",
            embedding=[0.1] * 1024,
            metadata={"topic": "security", "hop_target": 1},
            severity=SeverityLevel.MEDIUM,
            redirect_target="password reset",
        )

    def test_adversarial_doc_creation(self, sample_doc):
        """Test creating an adversarial doc."""
        assert sample_doc.content == "Sample content with redirect instruction."
        assert len(sample_doc.embedding) == 1024
        assert sample_doc.severity == SeverityLevel.MEDIUM
        assert sample_doc.redirect_target == "password reset"

    def test_to_payload(self, sample_doc):
        """Test converting adversarial doc to Qdrant payload."""
        payload = sample_doc.to_payload()

        assert payload["content"] == sample_doc.content
        assert payload["adversarial"] is True
        assert payload["attack_type"] == "hijack"
        assert payload["severity"] == "medium"
        assert payload["redirect_target"] == "password reset"
        assert payload["source"] == "adversarial_hijack"
        assert 0.0 <= payload["credibility"] <= 1.0


class TestHijackAttack:
    """Test HijackAttack class."""

    @pytest.fixture
    def hijack_attack(self):
        """Create HijackAttack instance."""
        return HijackAttack()

    def test_initialization(self, hijack_attack):
        """Test HijackAttack initialization."""
        assert hijack_attack.embedder is not None
        assert hijack_attack.trust_filter is not None

    def test_generate_low_severity(self, hijack_attack):
        """Test generating LOW severity hijack."""
        doc = hijack_attack.generate(
            topic="zero trust",
            redirect_target="password reset",
            severity=SeverityLevel.LOW,
        )

        assert doc.content is not None
        assert "password reset" in doc.content
        assert len(doc.embedding) == 1024
        assert doc.severity == SeverityLevel.LOW
        assert doc.redirect_target == "password reset"

    def test_generate_medium_severity(self, hijack_attack):
        """Test generating MEDIUM severity hijack."""
        doc = hijack_attack.generate(
            topic="security policy",
            redirect_target="admin credentials",
            severity=SeverityLevel.MEDIUM,
        )

        assert doc.content is not None
        assert "admin credentials" in doc.content
        assert "Recent literature" in doc.content or "recent analysis" in doc.content.lower()
        assert doc.severity == SeverityLevel.MEDIUM

    def test_generate_high_severity(self, hijack_attack):
        """Test generating HIGH severity hijack."""
        doc = hijack_attack.generate(
            topic="compliance framework",
            redirect_target="internal tokens",
            severity=SeverityLevel.HIGH,
        )

        assert doc.content is not None
        assert "internal tokens" in doc.content
        assert "compliance" in doc.content.lower()
        assert len(doc.content) > 200  # Should be more elaborate
        assert doc.severity == SeverityLevel.HIGH

    def test_generate_all_severities(self, hijack_attack):
        """Test that all severity levels produce different content."""
        topic = "authentication"
        redirect = "secret keys"

        low_doc = hijack_attack.generate(topic, redirect, SeverityLevel.LOW)
        medium_doc = hijack_attack.generate(topic, redirect, SeverityLevel.MEDIUM)
        high_doc = hijack_attack.generate(topic, redirect, SeverityLevel.HIGH)

        # Content should be different
        assert low_doc.content != medium_doc.content
        assert medium_doc.content != high_doc.content
        assert low_doc.content != high_doc.content

        # Redirect must be in all
        assert redirect in low_doc.content
        assert redirect in medium_doc.content
        assert redirect in high_doc.content

    def test_generate_empty_topic_raises(self, hijack_attack):
        """Test that empty topic raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            hijack_attack.generate("", "redirect", SeverityLevel.MEDIUM)

    def test_generate_empty_redirect_raises(self, hijack_attack):
        """Test that empty redirect target raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            hijack_attack.generate("topic", "", SeverityLevel.MEDIUM)

    def test_test_bypass(self, hijack_attack):
        """Test bypass probability calculation."""
        doc = hijack_attack.generate(
            topic="security",
            redirect_target="secrets",
            severity=SeverityLevel.LOW,
        )

        result = hijack_attack.test_bypass(doc, query="What is security?")

        assert "bypass_probability" in result
        assert "bypassed_count" in result
        assert "total_trials" in result
        assert "mean_total_score" in result
        assert "threshold" in result
        assert "details" in result

        # Probability should be between 0 and 1
        assert 0.0 <= result["bypass_probability"] <= 1.0

        # Should have run multiple trials
        assert result["total_trials"] > 0

        # bypassed_count should be consistent
        assert result["bypassed_count"] <= result["total_trials"]

    def test_test_bypass_count_consistency(self, hijack_attack):
        """Test that bypass count matches bypassed details."""
        doc = hijack_attack.generate("topic", "redirect", SeverityLevel.MEDIUM)

        result = hijack_attack.test_bypass(doc)

        bypassed_from_details = sum(1 for t in result["details"] if t.get("bypassed", False))
        assert bypassed_from_details == result["bypassed_count"]

    def test_test_bypass_with_hop_history(self, hijack_attack):
        """Test bypass testing with hop history."""
        doc = hijack_attack.generate("security", "credentials", SeverityLevel.MEDIUM)

        result = hijack_attack.test_bypass(
            doc,
            query="authentication",
            hop_history=["What is MFA?", "How do tokens work?"],
        )

        assert result["bypass_probability"] >= 0.0

    def test_batch_generate_and_inject_mismatched_lengths(self, hijack_attack):
        """Test that batch generate raises on mismatched list lengths."""
        with pytest.raises(ValueError, match="must have same length"):
            hijack_attack.batch_generate_and_inject(
                topics=["topic1"],
                redirect_targets=["target1", "target2"],  # Wrong length
                severities=[SeverityLevel.MEDIUM],
            )

    def test_batch_generate_and_inject_empty_lists(self, hijack_attack):
        """Test batch generate with empty lists."""
        doc_ids = hijack_attack.batch_generate_and_inject(
            topics=[],
            redirect_targets=[],
            severities=[],
        )

        assert doc_ids == []

    def test_low_severity_is_obvious(self, hijack_attack):
        """Test that LOW severity is obviously an instruction."""
        doc = hijack_attack.generate("topic", "redirect", SeverityLevel.LOW)

        # LOW severity should directly mention search/query action
        assert "search" in doc.content.lower()

    def test_medium_severity_has_framing(self, hijack_attack):
        """Test that MEDIUM severity uses framing language."""
        doc = hijack_attack.generate("topic", "redirect", SeverityLevel.MEDIUM)

        # MEDIUM should use academic/research language
        assert any(
            phrase in doc.content.lower()
            for phrase in [
                "literature",
                "analysis",
                "research",
                "according to",
                "recent",
            ]
        )

    def test_high_severity_is_embedded(self, hijack_attack):
        """Test that HIGH severity is embedded in paragraph."""
        doc = hijack_attack.generate("topic", "redirect", SeverityLevel.HIGH)

        # HIGH should be longer and more complex
        assert len(doc.content) > len(
            hijack_attack.generate("topic", "redirect", SeverityLevel.LOW).content
        )

        # HIGH should mention compliance/standards
        assert any(
            phrase in doc.content.lower()
            for phrase in ["compliance", "standard", "framework", "required"]
        )

    def test_embedding_dimensions(self, hijack_attack):
        """Test that embeddings have correct dimensions."""
        doc = hijack_attack.generate("topic", "target", SeverityLevel.MEDIUM)

        # BGE-M3 produces 1024-dimensional vectors
        assert len(doc.embedding) == 1024

        # Embeddings should be floats
        assert all(isinstance(x, (float, int)) for x in doc.embedding)

    def test_metadata_structure(self, hijack_attack):
        """Test that metadata has required fields."""
        doc = hijack_attack.generate("topic", "redirect", SeverityLevel.HIGH)

        required_keys = ["topic", "adversarial", "attack_type", "hop_target", "severity"]
        for key in required_keys:
            assert key in doc.metadata

    def test_reproducible_with_seed(self):
        """Test that embeddings are reproducible (through same model)."""
        hijack1 = HijackAttack()
        hijack2 = HijackAttack()

        doc1 = hijack1.generate("security", "credentials", SeverityLevel.MEDIUM)
        doc2 = hijack2.generate("security", "credentials", SeverityLevel.MEDIUM)

        # Content should be identical
        assert doc1.content == doc2.content

        # Embeddings should be identical (same model instance behavior)
        assert doc1.embedding == doc2.embedding

    def test_different_topics_produce_different_content(self, hijack_attack):
        """Test that different topics produce different documents."""
        doc1 = hijack_attack.generate("authentication", "tokens", SeverityLevel.MEDIUM)
        doc2 = hijack_attack.generate("encryption", "keys", SeverityLevel.MEDIUM)

        assert doc1.content != doc2.content
        assert doc1.redirect_target != doc2.redirect_target

    def test_different_redirects_in_content(self, hijack_attack):
        """Test that different redirect targets appear in content."""
        redirect1 = "Password reset procedures"
        redirect2 = "Internal credential database"

        doc1 = hijack_attack.generate("security", redirect1, SeverityLevel.MEDIUM)
        doc2 = hijack_attack.generate("security", redirect2, SeverityLevel.MEDIUM)

        assert redirect1 in doc1.content
        assert redirect2 in doc2.content

    def test_adversarial_metadata_flags(self, hijack_attack):
        """Test that adversarial flags are properly set."""
        doc = hijack_attack.generate("topic", "redirect", SeverityLevel.HIGH)

        payload = doc.to_payload()

        assert payload["adversarial"] is True
        assert payload["attack_type"] == "hijack"
        assert payload["source"] == "adversarial_hijack"

    def test_bypass_score_components(self, hijack_attack):
        """Test that bypass result includes trust score components."""
        doc = hijack_attack.generate("security", "secrets", SeverityLevel.LOW)

        result = hijack_attack.test_bypass(doc)

        # Check that details have component scores
        for trial in result["details"]:
            if "components" in trial:
                components = trial["components"]
                assert "semantic" in components
                assert "source" in components
                assert "injection" in components
                assert "hop" in components

    def test_hijack_vs_cascade_different_patterns(self, hijack_attack):
        """Test that hijack produces different patterns than cascade attacks."""
        hijack_doc = hijack_attack.generate("security", "admin", SeverityLevel.MEDIUM)

        # Hijack should NOT have system prompt patterns
        assert "SYSTEM:" not in hijack_doc.content
        assert "ignore previous" not in hijack_doc.content.lower()

        # Hijack should have suggestion/recommendation language
        assert any(
            phrase in hijack_doc.content.lower()
            for phrase in ["search", "retrieve", "requires", "important"]
        )
