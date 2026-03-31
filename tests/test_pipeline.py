from pipeline.graph import SecureStepGraph
from pipeline.retriever import RetrievedDocument
from trust_filter.filter import TrustScore


def test_pipeline_state_fields(monkeypatch):
    graph = SecureStepGraph()

    monkeypatch.setattr(graph.reformulator, "reformulate", lambda query, hop_history, context_window: query)
    monkeypatch.setattr(
        graph.retriever,
        "retrieve",
        lambda query: [RetrievedDocument(id="d1", content="zero trust basics", metadata={"source_type": "official"}, score=0.9)],
    )
    monkeypatch.setattr(
        graph.trust_filter,
        "score",
        lambda doc, query, hop_history, accepted_docs: TrustScore(semantic=90, source=90, injection=90, hop=90, total=90),
    )
    monkeypatch.setattr(graph.confidence_gate, "compute", lambda **kwargs: 95.0)
    monkeypatch.setattr(graph.generator, "generate", lambda query, context_docs, blocked_docs: "grounded answer")

    result = graph.run("What is zero trust?")

    assert "query" in result
    assert "hop_count" in result
    assert "context_window" in result
    assert "blocked_docs" in result
    assert "hop_queries" in result
    assert result["final_answer"] == "grounded answer"
