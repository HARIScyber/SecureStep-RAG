"""Unified LangChain LLM loader based on MODEL_PROVIDER."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel
from langchain_anthropic import ChatAnthropic
from langchain_community.chat_models import ChatOllama
from langchain_openai import ChatOpenAI


class LLMFactory:
    """Factory that returns a provider-specific LangChain chat model."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        load_dotenv()
        base = Path(__file__).resolve().parents[1]
        cfg_path = config_path or (base / "configs" / "models.yml")
        with cfg_path.open("r", encoding="utf-8") as f:
            self.config: Dict[str, Any] = yaml.safe_load(f)

    def load(self) -> BaseChatModel:
        provider = os.getenv("MODEL_PROVIDER", "openai").strip().lower()

        if provider == "openai":
            model_name = os.getenv("MODEL_NAME", self.config["openai"]["model"])
            temperature = float(self.config["openai"]["temperature"])
            return ChatOpenAI(model=model_name, temperature=temperature)

        if provider == "anthropic":
            model_name = os.getenv("MODEL_NAME", self.config["anthropic"]["model"])
            temperature = float(self.config["anthropic"]["temperature"])
            return ChatAnthropic(model=model_name, temperature=temperature)

        if provider in {"ollama", "llama3", "mistral"}:
            ollama_key = "llama3" if provider in {"ollama", "llama3"} else "mistral"
            model_name = os.getenv("MODEL_NAME", self.config["ollama"][ollama_key]["model"])
            temperature = float(self.config["ollama"][ollama_key]["temperature"])
            return ChatOllama(model=model_name, temperature=temperature)

        raise ValueError(
            "Unsupported MODEL_PROVIDER. Use one of: openai, anthropic, ollama, llama3, mistral."
        )
