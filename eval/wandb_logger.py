"""Weights & Biases logging helper for hop-level metrics."""

from __future__ import annotations

import os
from typing import Dict

import wandb
from dotenv import load_dotenv


class WandbLogger:
    """Logs evaluation metrics to Weights & Biases."""

    def __init__(self, project: str = "securestep-rag") -> None:
        load_dotenv()
        self.enabled = bool(os.getenv("WANDB_API_KEY"))
        self.run = wandb.init(project=project) if self.enabled else None

    def log(self, metrics: Dict[str, float], step: int) -> None:
        if self.run is not None:
            self.run.log(metrics, step=step)

    def finish(self) -> None:
        if self.run is not None:
            self.run.finish()
