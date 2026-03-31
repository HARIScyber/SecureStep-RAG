from pipeline.retriever import RetrievedDocument
from trust_filter.filter import TrustFilter


def test_trust_filter_combines_signals(monkeypatch):
    trust_filter = TrustFilter()

    monkeypatch.setattr(trust_filter.semantic_scorer, "score", lambda query, doc: 80.0)
    monkeypatch.setattr(trust_filter.source_scorer, "score", lambda doc: 90.0)
    monkeypatch.setattr(trust_filter.injection_scorer, "score", lambda query, doc, hop_history: 70.0)
    monkeypatch.setattr(trust_filter.hop_scorer, "score", lambda doc, accepted_docs: 60.0)

    doc = RetrievedDocument(id="1", content="safe text", metadata={"source_type": "official"})
    score = trust_filter.score(doc=doc, query="safe query", hop_history=[], accepted_docs=[])

    assert score.total > 0
    assert 0 <= score.injection <= 100
    assert trust_filter.is_trusted(score) == (score.total >= trust_filter.threshold)
