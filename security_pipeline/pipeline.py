"""
security_pipeline.py
------------------------------------------------------------------------------
A production-grade, extensible security pipeline built with the Pipeline Design
Pattern.  It supports

    • Intent classification (search vs reasoning)
    • Selective PII masking
    • Deterministic replacement / co-reference of company & person names
    • Full audit logging
    • Plug-and-play stages that can be added, removed, or reordered at runtime

Dependencies: standard library only (re, uuid, hashlib, logging, dataclasses).
No external services or persistent storage are used.
------------------------------------------------------------------------------
"""
from __future__ import annotations

import logging
import re
import uuid
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Iterable

# ---------------------------------------------------------------------------#
#                       CONFIGURATION & LOGGING                              #
# ---------------------------------------------------------------------------#
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
LOGGER = logging.getLogger("SecurityPipeline")

# ---------------------------------------------------------------------------#
#                       DATA CONTAINER                                        #
# ---------------------------------------------------------------------------#
@dataclass
class PipelineContext:
    original_text: str
    processed_text: str = ""
    coreference_resolved_text: str = ""  # For coreference resolution
    intent: str = ""  # "search" | "reasoning" | ""
    pii_entities: List[Dict[str, Any]] = field(default_factory=list)
    replacement_map: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

# ---------------------------------------------------------------------------#
#                       ABSTRACT PIPELINE STAGE                               #
# ---------------------------------------------------------------------------#
class PipelineStage(ABC):
    """Every concrete stage must implement .process()."""

    @abstractmethod
    def process(self, ctx: PipelineContext) -> PipelineContext:  # pragma: no cover
        """Process `ctx` in-place (may also return a new instance)."""
        raise NotImplementedError

# ---------------------------------------------------------------------------#
#                       PIPELINE ORCHESTRATOR                                #
# ---------------------------------------------------------------------------#
class SecurityPipeline:
    """
    Base orchestrator that simply runs stages in order.
    """

    def __init__(self, stages: Iterable[PipelineStage] | None = None) -> None:
        self.stages: List[PipelineStage] = list(stages) if stages else []

    # -------- pipeline mutation helpers -------- #
    def add_stage(self, stage: PipelineStage, position: int | None = None) -> None:
        if position is None:
            self.stages.append(stage)
        else:
            self.stages.insert(position, stage)

    def remove_stage(self, stage_cls: type[PipelineStage]) -> None:
        self.stages = [s for s in self.stages if not isinstance(s, stage_cls)]

    def process(self, text: str) -> PipelineContext:
        ctx = PipelineContext(original_text=text, processed_text=text)
        for stage in self.stages:
            ctx = stage.process(ctx)
        return ctx


