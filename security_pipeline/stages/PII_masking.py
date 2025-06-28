# ---------------------------------------------------------------------------#
#                       STAGE 3: CONDITIONAL PII MASKING                      #
# ---------------------------------------------------------------------------#
import logging
from typing import Dict
from security_pipeline.helper import _hash_mask, _multi_replace
from security_pipeline.pipeline import PipelineContext, PipelineStage


class PIIMaskStage(PipelineStage):
    """
    Masks all PII except company & person names.
    """
    IMMUNE_TYPES = {"COMPANY_NAME", "PERSON_NAME"}

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def process(self, ctx: PipelineContext) -> PipelineContext:
        if not ctx.pii_entities:
            return ctx

        masks: Dict[str, str] = {}
        for entity in ctx.pii_entities:
            val, ptype = entity["value"], entity["type"]
            if ptype in self.IMMUNE_TYPES:
                continue
            masks[val] = f'<{ptype}>'

        ctx.processed_text = _multi_replace(ctx.processed_text, masks)
        
        self.logger.debug("Applied %d PII masks", len(masks))
        return ctx
