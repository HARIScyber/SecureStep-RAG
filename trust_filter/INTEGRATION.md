"""
INTEGRATION GUIDE: TrustExplainer with SecureStepGraph Pipeline

This guide shows how to integrate TrustExplainer with your LangGraph pipeline
to store explanations for blocked documents and expose them via the dashboard.

## What is included

- TrustExplainer: Generates human-readable explanations for trust verdicts
- BlockExplanation dataclass: Structured explanation output
- SignalBreakdown: Per-signal analysis
- Verdict enum: PASSED/BLOCKED/SUSPICIOUS

## Integration Points

### 1. Pipeline Integration (graph.py)

In your `SecureStepGraph._trust_filter_docs()` method, add explainer:

```python
from trust_filter.explainer import TrustExplainer, BlockExplanation

class SecureStepGraph:
    def __init__(self, config_path: Optional[Path] = None) -> None:
        # ... existing code ...
        self.explainer = TrustExplainer()  # Add this line
        
    def _trust_filter_docs(self, state: GraphState) -> GraphState:
        '''Filter documents using trust scores and generate explanations.'''
        
        retrieved_docs = state["retrieved_docs"]
        accepted_docs = state.get("accepted_docs", [])
        hop_queries = state.get("hop_queries", [])
        blocked_docs = state.get("blocked_docs", [])
        
        for doc in retrieved_docs:
            # Score the document
            trust_score = self.trust_filter.score(
                doc=doc,
                query=state["current_query"],
                hop_history=hop_queries,
                accepted_docs=accepted_docs,
            )
            
            # Check if trusted
            if self.trust_filter.is_trusted(trust_score):
                state["accepted_docs"].append(doc)
            else:
                # Generate explanation for blocked document
                explanation = self.explainer.explain(
                    doc=doc,
                    trust_score=trust_score,
                    query=state["current_query"],
                    threshold=self.trust_filter.threshold,
                    hop_history=hop_queries,
                    accepted_docs=accepted_docs,
                )
                
                # Store in blocked_docs with explanation
                blocked_docs.append({
                    "document": doc.dict(),
                    "trust_score": trust_score.dict(),
                    "explanation": explanation.as_dict(),
                    "hop": state["hop_count"],
                    "timestamp": datetime.now().isoformat(),
                })
        
        state["blocked_docs"] = blocked_docs
        return state
```

### 2. Dashboard API Integration

Each blocked document includes a `BlockExplanation` serializable to JSON:

```python
from fastapi import FastAPI
from trust_filter import TrustExplainer, BlockExplanation

app = FastAPI()

@app.get("/api/dashboard/blocked-documents")
async def get_blocked_documents(query_id: str):
    """Retrieve detailed explanations for blocked documents."""
    # Fetch from your state store
    blocked_docs = fetch_blocked_docs_for_query(query_id)
    
    # Each item includes explanation.as_dict():
    return {
        "query": query_id,
        "blocked_count": len(blocked_docs),
        "documents": [
            {
                "document": bd["document"],
                "trust_scores": bd["trust_score"],
                "explanation": bd["explanation"],  # BlockExplanation.as_dict()
                "hop": bd["hop"],
            }
            for bd in blocked_docs
        ]
    }
```

### 3. Notebook Display Integration

In Jupyter notebooks (eval/ablation.py, etc.):

```python
from trust_filter import BlockExplanation
from IPython.display import Markdown, display

# After running evaluation
for blocked_doc in blocked_documents:
    explanation = BlockExplanation(
        verdict=blocked_doc["explanation"]["verdict"],
        # ... reconstruct from dict ...
    )
    # Display markdown render
    display(Markdown(explanation.as_markdown()))
```

### 4. Audit Log Integration

For enterprise compliance and audit tracks:

```python
import json
from datetime import datetime
from trust_filter import TrustExplainer

def log_blocked_document(doc, trust_score, explanation):
    """Log blocked document to audit system."""
    audit_entry = {
        "event_type": "DOCUMENT_BLOCKED",
        "timestamp": datetime.now().isoformat(),
        "document_id": doc.metadata.get("id"),
        "source": doc.metadata.get("source"),
        "verdict": explanation.verdict.value,
        "confidence": explanation.confidence,
        "triggered_rules": explanation.triggered_rules,
        "scores": trust_score.dict(),
        "primary_reason": explanation.primary_reason,
        "recommendation": explanation.recommendation,
    }
    
    # Send to audit system (Splunk, DataDog, etc.)
    audit_logger.info(json.dumps(audit_entry))
```

## Data Structures

### BlockExplanation.as_dict()

```json
{
    "verdict": "BLOCKED",
    "primary_reason": "Critical injection risk: 25/100 (likely adversarial payload detected)",
    "signal_breakdown": {
        "semantic_score": 78.5,
        "semantic_reason": "Good semantic alignment with query",
        "source_score": 18.0,
        "source_reason": "Source marked as adversarial (unknown)",
        "injection_score": 25.0,
        "injection_reason": "Critical injection risk: 25/100 (likely adversarial payload detected)",
        "hop_score": 35.2,
        "hop_reason": "Significant drift: 35/100 (major topic shift detected)"
    },
    "triggered_rules": [
        "fake_system_prompt_pattern('[INST]')",
        "imperative_verb_detected('ignore')",
        "embedding_anomaly(query_similarity_low, penalty=20)",
        "hop_redirect_detected(latest_hop='What is ML?', penalty=10)"
    ],
    "confidence": 92.3,
    "recommendation": "Quarantine. Document exhibits injection attack indicators. Review triggeredRules before manual inclusion."
}
```

### BlockExplanation.as_markdown()

Produces human-readable markdown for notebooks:

```markdown
# Trust Filter Verdict: BLOCKED
**Confidence:** 92%

## Primary Reason
Critical injection risk: 25/100 (likely adversarial payload detected)

## Signal Scores
- **Semantic Relevance:** 78.5/100 — Good semantic alignment with query
- **Source Credibility:** 18.0/100 — Source marked as adversarial (unknown)
- **Injection Risk:** 25.0/100 — Critical injection risk
- **Hop Consistency:** 35.2/100 — Significant drift detected

## Triggered Rules
- fake_system_prompt_pattern('[INST]')
- imperative_verb_detected('ignore')
- embedding_anomaly(query_similarity_low, penalty=20)
- hop_redirect_detected(latest_hop='What is ML?', penalty=10)

## Recommendation
Quarantine. Document exhibits injection attack indicators. Review triggeredRules before manual inclusion.
```

## Trust Signals with Explanations

### Semantic Signal
- **90+:** Excellent semantic alignment
- **75-89:** Good semantic alignment
- **55-74:** Moderate alignment
- **35-54:** Weak alignment
- **<35:** Very weak alignment

### Source Signal
- **Official/Paper sources:** Higher prior (0.9-0.95)
- **Internal/Web sources:** Medium prior (0.65-0.85)
- **Forum/Unknown:** Lower prior (0.4-0.45)
- **Adversarial flag:** Credibility capped at 0.2

### Injection Signal (Lower = Worse)
- **85+:** Low injection risk
- **70-84:** Moderate risk (minor patterns)
- **50-69:** Elevated risk (multiple patterns)
- **30-49:** High risk (strong indicators)
- **<30:** Critical risk (likely adversarial)

Patterns detected:
- Imperative verbs: ignore, disregard, forget, pretend, output, reveal
- Fake system prompts: [INST], <|im_start|>, SYSTEM:, <|system|>
- Redirect commands: search for, retrieve document, query for, next hop

### Hop Consistency Signal
- **85+:** Excellent drift consistency
- **70-84:** Good consistency
- **55-69:** Moderate drift
- **35-54:** Significant drift
- **<35:** Critical drift (multihop attack)

## Confidence Scoring

Confidence (0-100%) factors:
1. **Distance from threshold** - Extreme scores = high confidence
2. **Signal agreement** - All signals aligned = high confidence
3. **Rule triggers** - More rules = higher confidence in block

## Example Usage

```python
# See trust_filter/example_usage.py for complete examples:

# Dashboard Integration
example_dashboard_integration()  # JSON API responses

# Audit Logs
example_audit_log_entry()  # Compliance logging

# Multi-Hop Evaluation
example_multi_hop_evaluation()  # End-to-end evaluation

# Signal Comparison
example_signal_comparison()  # Detailed signal analysis
```

## Testing

Run unit tests with:

```bash
pytest tests/test_explainer.py -v
```

Test coverage includes:
- BlockExplanation serialization (dict, markdown)
- Rule detection (imperative, system prompts, redirects)
- Signal explanations for all score ranges
- Primary reason selection (worst signal)
- Confidence computation
- Recommendation generation
- Integration with injection/hop/semantic/source scorers

## Performance Notes

- Explanation generation is instant (<1ms) as it doesn't require additional scoring
- All scores were already computed by TrustFilter
- Rule detection is regex-based and very fast
- Suitable for real-time dashboard updates
- Can be cached by explanation hash if needed

## Enterprise Features

1. **Trust Inspector Dashboard** - Visual explanation of each blocked document
2. **Audit Trails** - Complete record with recommendations
3. **Compliance Export** - JSON/CSV output with explanations
4. **Per-Query Analytics** - Track which rules trigger most frequently
5. **False Positive Feedback** - Mark explanations as helpful/unhelpful

## Future Enhancements

- [ ] Visualization of signal contributions (waterfall chart)
- [ ] NLP-based rule suggestion for custom policies
- [ ] Explainability metrics tracking
- [ ] A/B testing different confidence thresholds
- [ ] Integration with model interpretability tools (LIME, SHAP)
"""
