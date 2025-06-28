# ---------------------------------------------------------------------------#
#                       STAGE 1: INTENT CLASSIFICATION                        #
# ---------------------------------------------------------------------------#
import logging
from security_pipeline.pipeline import PipelineContext, PipelineStage
from fastcoref import spacy_component
import spacy

nlp = spacy.load("en_core_web_lg")
nlp.add_pipe("fastcoref")


class CoreferenceStage(PipelineStage):
    

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def process(self, ctx: PipelineContext) -> PipelineContext:
        text = ctx.original_text
        resolve_doc = nlp(text,component_cfg={"fastcoref": {'resolve_text': True}})
        ctx.coreference_resolved_text = resolve_doc._.resolved_text
        ctx.processed_text = ctx.coreference_resolved_text

        self.logger.debug("Resolved text as '%s'", ctx.processed_text)
        return ctx
