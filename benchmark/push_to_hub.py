"""Publishes SecureStep-RAG benchmark dataset to Hugging Face Hub."""

from __future__ import annotations

from pathlib import Path

from datasets import DatasetDict, load_dataset


def main(repo_id: str = "securestep/securestep-rag-benchmark") -> None:
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "benchmark" / "data"

    dataset = DatasetDict(
        {
            "clean": load_dataset("json", data_files=str(data_dir / "clean_docs.jsonl"), split="train"),
            "injected": load_dataset("json", data_files=str(data_dir / "injected_docs.jsonl"), split="train"),
            "queries": load_dataset("json", data_files=str(data_dir / "hop_queries.jsonl"), split="train"),
        }
    )
    dataset.push_to_hub(repo_id)
    print(f"Dataset pushed to {repo_id}")


if __name__ == "__main__":
    main()
