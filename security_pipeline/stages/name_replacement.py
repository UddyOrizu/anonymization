# ---------------------------------------------------------------------------#
#                       STAGE 4: NAME REPLACEMENT (reasoning)                 #
# ---------------------------------------------------------------------------#
import logging
import random
from typing import Dict
from security_pipeline.helper import _multi_replace, _stable_uuid
from security_pipeline.pipeline import PipelineContext, PipelineStage


class NameReplacementStage(PipelineStage):
    """
    For 'reasoning' intent only:
        • Replace company / person names with deterministic pseudonyms
        • Maintain mapping in ctx.replacement_map
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def generate_random_person_name(self) -> str:
        """Generate a random person name."""
        first_names = [
            "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Jamie", "Avery", "Peyton", "Quinn","Abaobi"
        ]
        last_names = [
            "SmithDoe", "JohnsonDoe", "LeeDoe", "BrownDoe", "GarciaDoe", "MartinezDoe", "DavisDoe", "ClarkDoe", "LewisDoe", "WalkerDoe","OlufemiDoe"
        ]
        return f"{random.choice(first_names)} {random.choice(last_names)}"

    def generate_random_company_name(self) -> str:
        """Generate a random company name."""
        prefixes = [
            "ABCTech", "ABCGlobal", "ABCNextGen", "XYZPioneer", "ABCVision", "ABCQuantum", "XYZBlue", "ABCGreen", "DEFPrime", "123Dynamic"
        ]
        suffixes = [
            "Solutions", "Systems", "Industries", "Enterprises", "Group", "Technologies", "Holdings", "Partners", "Labs", "Networks"
        ]
        return f"{random.choice(prefixes)} {random.choice(suffixes)}"


    def process(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.intent != "reasoning":
            return ctx

        replacements: Dict[str, str] = {}
        try:
            for entity in ctx.pii_entities:
                etype, val = entity["type"], entity["value"]
                if etype == "PERSON_NAME":
                    alias = self.generate_random_person_name()
                elif etype == "COMPANY_NAME":
                    alias = self.generate_random_company_name()
                else:
                    continue
                replacements[val] = alias
                ctx.replacement_map[val] = alias

            ctx.processed_text = _multi_replace(ctx.processed_text, replacements)
            self.logger.debug("Replaced %d names with aliases", len(replacements))
            return ctx
        except Exception as e:
            self.logger.error("Error during name replacement: %s", str(e))
            raise e