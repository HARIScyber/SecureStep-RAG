"""Arize Phoenix tracing utilities for pipeline execution."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from time import perf_counter


@dataclass
class TraceSpan:
    name: str
    duration_ms: float


@contextmanager
def trace_span(name: str):
    start = perf_counter()
    try:
        yield
    finally:
        duration = (perf_counter() - start) * 1000.0
        print(TraceSpan(name=name, duration_ms=duration))
