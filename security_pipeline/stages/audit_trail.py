# ---------------------------------------------------------------------------#
#                       STAGE 5: AUDIT / FINAL REPORT                         #
# ---------------------------------------------------------------------------#
import logging

from security_pipeline.pipeline import PipelineContext, PipelineStage
from security_pipeline.stages.name_replacement import NameReplacementStage


class AuditStage(PipelineStage):
    """Adds a concise audit trail entry to ctx.metadata."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def process(self, ctx: PipelineContext) -> PipelineContext:
        ctx.metadata["audit"] = {
            "intent": ctx.intent,
            "pii_discovered": len(ctx.pii_entities),
            "masked_entities": [
                e for e in ctx.pii_entities if e["type"] not in NameReplacementStage.__name__
            ],
            "name_mapping": ctx.replacement_map,
        }
        # Inline log (do NOT log raw text)
        self.logger.info(
            "Pipeline complete | intent=%s | pii=%d | replacements=%d",
            ctx.intent,
            len(ctx.pii_entities),
            len(ctx.replacement_map),
        )
        return ctx