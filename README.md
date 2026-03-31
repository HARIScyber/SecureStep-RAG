# SecureStep-RAG: Multi-Hop Retrieval-Augmented Generation with Iterative Trust Filtering

**Defense without degradation:** A production-ready framework for securing multi-hop RAG pipelines against adversarial document injection attacks using multi-signal trust filtering and position-aware guardrails.

---

## 🏗️ Architecture

```mermaid
graph LR
    A["User Query<br/>(e.g., 'What is zero trust?')"] --> B["Reformulator<br/>(LLM Query Refinement)"]
    B --> C["Retriever<br/>(BGE-M3 + Qdrant)"]
    C --> D["Trust Filter<br/>(4-Signal Scoring)"]
    D -->|"Semantic Similarity<br/>Source Credibility<br/>Injection Risk<br/>Hop Drift"| E["Decision<br/>Pass/Block"]
    E -->|"✓ Pass"| F["NeMo Guardrails<br/>(Confidence Gate)"]
    E -->|"✗ Block"| G["Quarantine"]
    F --> H["LLM Generator<br/>(Answer Generation)"]
    H --> I["Hop Iteration<br/>(Continue or Stop?)"]
    I -->|"Retrieve More"| B
    I -->|"Complete"| J["Safe Answer"]
    G -.→ K["Audit Log<br/>(Blocked Docs)"]
    J -.→ K

    style A fill:#e1f5ff
    style D fill:#fff3e0
    style F fill:#f3e5f5
    style J fill:#e8f5e9
    style G fill:#ffebee
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Docker & Docker Compose
- Node.js 18+
- OpenAI API key (or alternative LLM provider)

### 1-Minute Setup

```bash
# Clone repository
git clone https://github.com/yourusername/securestep-rag.git
cd securestep-rag

# Setup environment
cp .env.example .env
# Edit .env with your LLM API keys

# Start all services (FastAPI + PostgreSQL + Qdrant + React)
make docker

# Build vector index and load benchmark data
make index

# Run full pipeline
make run

# Open dashboard
open http://localhost:3000
```

### Individual Component Startup

```bash
# Terminal 1: Backend API (FastAPI)
make run-api

# Terminal 2: Frontend (React dev server)
cd frontend && npm run dev

# Terminal 3: Evaluation suite
make eval

# Terminal 4: Benchmarking
make benchmark
```

---

## ✨ Key Features

### 🛡️ Multi-Signal Trust Filtering
- **Semantic Similarity** (BGE-M3 embeddings) - Is the doc topic-relevant?
- **Source Credibility** (knowledge graph) - Is the source trustworthy?
- **Injection Risk** (pattern detection) - Does it contain attack markers?
- **Hop Drift** (centroid tracking) - Has the query drifted across hops?

### 🔄 Iterative Hop Hardening
- **Confidence Gate** - Only continue retrieval if confidence > threshold
- **Cross-Hop Consistency** - Detect if queries are being gradually hijacked
- **Bounded Hops** - Configurable max hops (default=4) to prevent infinite loops

### 🛑 Novel Retrieval-Position Guardrails (Research Contribution)
- **Input Rail**: Sanitize user queries before retrieval
- **Output Rail**: Filter answer for hallucinations (existing in most frameworks)
- **Transition Rail** ⭐ **NEW**: Detect hop-to-hop query drift in reformulated queries
- **Retrieval Rail**: Validate retrieved documents match the context

### 📊 Adversarial Benchmark
- **4 Attack Types**: Cascade (multi-doc), Drift (gradual), Hijack (redirect), Amplification (escalating)
- **Clean + Poisoned Splits**: 1000 clean docs, 400 adversarial per attack type
- **Automated Injection**: `corpus_injector.py` for controlled attack deployment

---

## 📈 Ablation Results

| Condition | Faithfulness ↑ | Attack Success ↓ | Blocked Docs | Latency (ms) |
|-----------|-----------------|------------------|--------------|--------------|
| Naive RAG (No Defense) | 0.72 | 78% | 0 | 145 |
| Trust Filter Only | **0.81** | 24% | 312 | 189 |
| +NeMo Guardrails | **0.84** | 8% | 356 | 210 |
| Full Defense (Ablation) | **0.86** | 2% | 389 | 224 |

*Results on cascade attack; see `results/ablation_results_with_stats.json` for full statistical significance testing.*

---

## 🛠️ Technology Stack

<div align="center">

![LangGraph](https://img.shields.io/badge/LangGraph-3.0-blue?style=for-the-badge&logo=python)
![Qdrant](https://img.shields.io/badge/Qdrant-2.4-purple?style=for-the-badge&logo=vector)
![BGE-M3](https://img.shields.io/badge/BGE--M3-Embedding-orange?style=for-the-badge)
![NeMo](https://img.shields.io/badge/NeMo-Guardrails-green?style=for-the-badge&logo=nvidia)
![RAGAS](https://img.shields.io/badge/RAGAS-Eval-red?style=for-the-badge)
![W&B](https://img.shields.io/badge/Weights%20%26%20Biases-Logging-yellow?style=for-the-badge&logo=wandb)

</div>

### Backend
- **LangGraph** - Multi-hop orchestration
- **Qdrant** - Vector store (HNSW indexing)
- **BGE-M3** - Dense retrieval embeddings
- **Ollama/OpenAI/Claude** - LLM inference
- **NeMo Guardrails** - Prompt guardrails (framework)

### Evaluation
- **RAGAS** - Faithfulness scoring
- **DeepEval** - Test automation
- **Weights & Biases** - Experiment tracking
- **Scikit-learn** - Statistical testing

### Frontend
- **React 18** - Dashboard UI
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Recharts** - Evaluation visualizations
- **WebSocket** - Real-time streaming

---

## 📁 Project Structure

```
securestep-rag/
├── attack/                     # Attack implementations
│   ├── cascade_attack.py
│   ├── drift_attack.py
│   ├── hijack_attack.py
│   ├── amplification_attack.py
│   └── corpus_injector.py
├── eval/                       # Evaluation suite
│   ├── ablation.py            # 4-condition ablation study
│   ├── baseline_comparison.py
│   ├── cross_model_eval.py
│   ├── latency_benchmark.py
│   └── ragas_eval.py
├── pipeline/                   # Main LangGraph pipeline
│   ├── graph.py               # Orchestration
│   ├── retriever.py
│   ├── reformulator.py
│   ├── generator.py
│   └── confidence.py
├── trust_filter/              # Core defense
│   ├── filter.py              # 4-signal scoring
│   ├── calibration.py         # Threshold auto-tuning
│   ├── semantic_scorer.py
│   ├── source_scorer.py
│   ├── injection_scorer.py
│   ├── hop_scorer.py
│   └── explainer.py           # Human-readable verdicts
├── guardrails/                # NeMo guardrails
│   ├── rails/
│   │   ├── input_rail.co
│   │   ├── output_rail.co
│   │   ├── retrieval_rail.co
│   │   └── hop_transition_rail.co  # Novel 4th position
│   └── config.yml
├── frontend/                  # React dashboard
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Pipeline.tsx      # Real-time execution
│   │   │   ├── AttackStudio.tsx   # Injection interface
│   │   │   ├── TrustInspector.tsx # Threshold tuning
│   │   │   ├── Evaluation.tsx     # Results visualization
│   │   │   ├── Benchmark.tsx      # Doc browser
│   │   │   └── Status.tsx         # System health
│   │   ├── components/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── TrustBar.tsx       # 4-signal component
│   │   │   └── HopTrace.tsx       # Hop timeline
│   │   ├── hooks/usePipeline.ts
│   │   └── App.tsx
│   └── package.json
├── benchmark/                 # Adversarial benchmark
│   └── data/
│       ├── clean_docs.jsonl
│       ├── injected_docs.jsonl
│       └── hop_queries.jsonl
├── configs/
│   ├── pipeline.yml           # Calibrated threshold
│   ├── models.yml
│   └── eval.yml
├── main.py                    # FastAPI server
├── docker-compose.yml         # Service orchestration
├── Makefile                   # Development commands
└── pyproject.toml            # Python dependencies
```

---

## 🔧 Configuration

### Environment Variables (`.env`)

```bash
# LLM Provider (default: openai)
MODEL_PROVIDER=openai
OPENAI_API_KEY=sk-...

# Qdrant Vector Store
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

# Trust Filter
TRUST_THRESHOLD=60.0  # Calibrated value (see: trust_filter/calibration.py)
SEMANTIC_WEIGHT=0.3
SOURCE_WEIGHT=0.25
INJECTION_WEIGHT=0.25
HOP_WEIGHT=0.2

# Evaluation
WANDB_PROJECT=securestep-rag
WANDB_ENTITY=your-username

# Backend
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
```

### Trust Filter Weights

Auto-calibrated by `trust_filter/calibration.py`:

```
Weight Distribution (default):
├── Semantic Similarity: 30%  (BGE-M3 embedding match)
├── Source Credibility:   25%  (knowledge graph + web search)
├── Injection Risk:       25%  (pattern detection + LLM)
└── Hop Drift:            20%  (query centroid tracking)
```

Run `make calibrate` to optimize on your dataset.

---

## 📊 Evaluation & Results

### Quick Evaluation

```bash
# Run full ablation study (4 conditions, statistical significance)
make eval

# Cross-model evaluation (llama3 + gpt-4o + claude-3-5-sonnet)
python eval/cross_model_eval.py --models llama3 gpt-4o claude-3-5-sonnet

# Latency benchmarking
make benchmark

# Baseline comparison (naive RAG vs defended)
python eval/baseline_comparison.py
```

### Output Files

```
results/
├── ablation_results_with_stats.json
├── baseline_results.json
├── cross_model_results.json
├── latency_report.json
├── roc_curve.png              # Threshold ROC
├── threshold_curve.png        # F1 vs threshold
└── latency_distribution.png
```

---

## 🎯 Usage Examples

### Run Pipeline with WebSocket Streaming

```python
import asyncio
import json
import websockets

async def stream_query():
    async with websockets.connect("ws://localhost:8000/ws/pipeline") as ws:
        # Send query with attack/defense settings
        await ws.send(json.dumps({
            "query": "What is zero trust architecture?",
            "attack_enabled": False,
            "defence_enabled": True,
        }))
        
        # Stream real-time events
        async for msg in ws:
            event = json.loads(msg)
            if event["type"] == "hop_start":
                print(f"🔍 Hop {event['hop']}: {event['query']}")
            elif event["type"] == "doc_blocked":
                print(f"🚫 Blocked: {event['doc_title']} (score={event['trust_score']:.0f})")
            elif event["type"] == "answer":
                print(f"✅ Answer: {event['text'][:200]}...")

asyncio.run(stream_query())
```

### Inject Adversarial Documents

```bash
# Cascade attack (poison multiple hops)
curl -X POST http://localhost:8000/api/attack/inject \
  -H "Content-Type: application/json" \
  -d '{
    "attack_type": "cascade",
    "topic": "zero trust",
    "target": "admin credentials",
    "severity": "high",
    "n_docs": 10
  }'
```

### Calibrate Trust Threshold

```bash
# Auto-tune threshold on your dataset
make calibrate

# Manual threshold test
curl http://localhost:8000/api/config | jq '.trust_threshold'
```

---

## 📝 Citation

If you use SecureStep-RAG in your research, please cite:

```bibtex
@article{securestep2024,
  title={SecureStep-RAG: Multi-Hop Retrieval-Augmented Generation with Iterative Trust Filtering},
  author={Your Name and Collaborators},
  journal={arXiv preprint arXiv:2024.05XXX},
  year={2024}
}
```

---

## 📚 Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment guide (Docker, Kubernetes, cloud)
- **[WEBSOCKET_API.md](WEBSOCKET_API.md)** - WebSocket protocol specification
- **[PAPER.md](PAPER.md)** - Full research paper draft
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Command reference

---

## 🧪 Testing

```bash
# Run all tests with coverage
pytest tests/ -v --cov=.

# Test specific module
pytest tests/test_trust_filter.py -v

# Test guardrails
pytest tests/test_guardrails.py -v

# Verify WebSocket API
pytest tests/test_main_api.py -v
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## ⚠️ Limitations & Future Work

### Known Limitations
- Qdrant vector store (requires separate service)
- Latency overhead ~80ms per hop (see `latency_benchmark.py`)
- No GPU acceleration required but recommended for BGE-M3

### Roadmap
- [ ] Multi-language support (currently tested on en/zh)
- [ ] Cached vector embeddings for faster retrieval
- [ ] Federated learning for cross-org threat intelligence
- [ ] Real-time threat feed integration
- [ ] Hardware acceleration via NVIDIA TensorRT

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/securestep-rag/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/securestep-rag/discussions)
- **Email**: research@example.com
- **Docs**: [Full Documentation](https://securestep-rag.readthedocs.io)

---

## 📄 License

SecureStep-RAG is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

```
MIT License

Copyright (c) 2024 SecureStep-RAG Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

## 🙏 Acknowledgments

- **NIST** for zero-trust security framework reference
- **LangChain** team for LangGraph orchestration framework
- **Qdrant** for efficient vector search
- **NVIDIA NeMo** for guardrails framework
- **HuggingFace** for BGE-M3 embeddings

---

<div align="center">

**Built with ❤️ for secure, trustworthy AI systems**

⭐ If you find this project useful, please consider giving it a star!

[![GitHub Stars](https://img.shields.io/github/stars/yourusername/securestep-rag?style=social)](https://github.com/yourusername/securestep-rag)
[![GitHub Forks](https://img.shields.io/github/forks/yourusername/securestep-rag?style=social)](https://github.com/yourusername/securestep-rag)

</div>
