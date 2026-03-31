from attack.cascade_attack import build_cascade_document
from attack.drift_attack import generate_drift_sequence


def test_cascade_payload_contains_redirect_patterns():
    doc = build_cascade_document("zero trust")
    assert "SYSTEM:" in doc
    assert "search for" in doc.lower()


def test_drift_sequence_monotonic_shift():
    seq = generate_drift_sequence("api key rotation")
    assert len(seq) == 4
    assert seq[0] != seq[-1]
