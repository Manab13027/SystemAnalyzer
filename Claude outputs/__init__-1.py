"""Detector modules. Each exposes a class with .name, .kind, and
.analyze(payload) -> list[Alert]."""

from .base import Detector
from .log_analyzer import LogAnalyzer
from .content_analyzer import ContentAnalyzer
from .endpoint_analyzer import EndpointAnalyzer
from .llm_defense import LLMDefense

ALL_DETECTORS = [LogAnalyzer, ContentAnalyzer, EndpointAnalyzer, LLMDefense]

__all__ = [
    "Detector",
    "LogAnalyzer",
    "ContentAnalyzer",
    "EndpointAnalyzer",
    "LLMDefense",
    "ALL_DETECTORS",
]
