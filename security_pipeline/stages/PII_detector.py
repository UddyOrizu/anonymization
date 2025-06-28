# ---------------------------------------------------------------------------#
#                       STAGE 2: PII DETECTION                                #
# ---------------------------------------------------------------------------#
import re
import logging
from typing import Dict, List, Set, Optional, Tuple
import spacy
from presidio_analyzer import AnalyzerEngine
from security_pipeline.pipeline import PipelineContext, PipelineStage


class PIIDetectorStage(PipelineStage):
    """
    Regex-based PII detector (no external libraries).
    Detected entities are saved into `ctx.pii_entities`:
        { "type": <PII_TYPE>, "value": <matched_text> }
    """

    # Compile once for performance
    _EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    _PHONE_RE = re.compile(r"\b(?:\+?\d{1,3})?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
    _IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    _SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    _CREDIT_CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
    # Simplistic address pattern (street num + word tokens)
    _ADDRESS_RE = re.compile(r"\b\d{1,5}\s+\w+(?:\s+\w+){0,4}\s(?:Street|St|Road|Rd|Avenue|Ave|Blvd|Lane|Ln|Way)\b",flags=re.IGNORECASE,)
    # Person name: two or more consecutive capitalised words


    PATTERNS = {
        "EMAIL": _EMAIL_RE,
        "PHONE": _PHONE_RE,
        "IP": _IP_RE,
        "SSN": _SSN_RE,
        "CREDIT_CARD": _CREDIT_CARD_RE,
        "ADDRESS": _ADDRESS_RE,
    }

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize spaCy model
        try:
            self.nlp = spacy.load("en_core_web_lg")
            self.logger.info("Successfully loaded spaCy model for entity detection")
            self.spacy_available = True
        except Exception as e:
            self.logger.error(f"Error loading spaCy model: {e}")
            self.spacy_available = False
            
        # Initialize Presidio Analyzer
        try:
            self.analyzer = AnalyzerEngine()
            # Create NLP engine with spaCy
            # self.presidio_nlp_engine = NlpEngineProvider(nlp_engine_name="spacy").create_engine()
            
            # # Create analyzer with default recognizers
            # registry = RecognizerRegistry()
            # registry.load_predefined_recognizers()
            # self.analyzer = AnalyzerEngine(
            #     nlp_engine=self.presidio_nlp_engine,
            #     registry=registry
            # )
            self.logger.info("Successfully initialized Presidio Analyzer")
            self.presidio_available = True
        except Exception as e:
            self.logger.error(f"Error initializing Presidio Analyzer: {e}")
            self.presidio_available = False

    def process(self, ctx: PipelineContext) -> PipelineContext:
        """
        Process the input text to detect PII entities using multiple approaches:
        1. Regex-based detection (baseline)
        2. spaCy NER (if available)
        3. Presidio Analyzer (if available)
        
        The results are merged, with priority given to more specific entity types.
        """
        # Start with regex detection (always available)
        entities = self.regex_based_pii_detection(ctx.coreference_resolved_text)
        
        # Add spaCy entities if available
        if self.spacy_available:
            try:
                spacy_entities = self.spacy_entity_detection(ctx.coreference_resolved_text)
                entities.extend(spacy_entities)
                self.logger.debug(f"Added {len(spacy_entities)} entities from spaCy")
            except Exception as e:
                self.logger.error(f"Error in spaCy entity detection: {e}")
        
        # Add Presidio entities if available
        if self.presidio_available:
            try:
                presidio_entities = self.presidio_entity_detection(ctx.coreference_resolved_text)
                entities.extend(presidio_entities)
                self.logger.debug(f"Added {len(presidio_entities)} entities from Presidio")
            except Exception as e:
                self.logger.error(f"Error in Presidio entity detection: {e}")
        
        # Deduplicate and merge entities
        merged_entities = self.merge_entities(entities)
        ctx.pii_entities = merged_entities
        
        self.logger.info(f"Total PII entities detected: {len(merged_entities)}")
        return ctx
    
    def regex_based_pii_detection(self, text: str) -> List[Dict[str, str]]:
        """
        Perform regex-based PII detection on the given text.
        This is a baseline approach that uses regular expressions to identify 
        common patterns like emails, phone numbers, SSNs, etc.
        
        Args:
            text: The input text to analyze
            
        Returns:
            A list of detected PII entities
        """
        found: List[Dict[str, str]] = []

        for pii_type, pattern in self.PATTERNS.items():
            for match in pattern.finditer(text):
                found.append({"type": pii_type, "value": match.group(0)})
                self.logger.debug(f"Regex detected: {match.group(0)} as {pii_type}")

        # No need to deduplicate here as we'll merge all entities later
        self.logger.debug(f"Regex detection found {len(found)} entities")
        return found
    
    def spacy_entity_detection(self, text: str) -> List[Dict[str, str]]:
        """
        Use spaCy's named entity recognition to detect PII entities in the text.
        
        This method identifies people, organizations, locations, dates, etc.
        using spaCy's pre-trained NER model.
        
        Args:
            text: The input text to analyze
            
        Returns:
            A list of PII entities in the format {"type": entity_type, "value": entity_text}
        """
        # Entity type mapping: spaCy -> our standardized types
        SPACY_ENTITY_MAP = {
            "PERSON": "PERSON_NAME",
            "ORG": "COMPANY_NAME",
            "GPE": "LOCATION",  # Countries, cities, states
            "LOC": "LOCATION",  # Non-GPE locations, mountain ranges, bodies of water
            "DATE": "DATE",
            "TIME": "TIME",
            "MONEY": "FINANCIAL",
            "CARDINAL": "NUMBER",
            "ORDINAL": "NUMBER",
            "QUANTITY": "QUANTITY",
            "PRODUCT": "PRODUCT",
            "EMAIL": "EMAIL",
            "PHONE": "PHONE",
            "URL": "URL",
        }
        
        found = []
        doc = self.nlp(text)
        
        # Extract standard named entities
        for ent in doc.ents:
            if ent.label_ in SPACY_ENTITY_MAP:
                # Map to standardized entity type
                entity_type = SPACY_ENTITY_MAP[ent.label_]
                found.append({
                    "type": entity_type,
                    "value": ent.text
                })
                self.logger.debug(f"spaCy detected: {ent.text} as {entity_type}")
        
        # Use token patterns to detect entities that spaCy might miss
        found.extend(self._additional_spacy_patterns(doc))
        
        return found
        
    def _additional_spacy_patterns(self, doc) -> List[Dict[str, str]]:
        """
        Apply additional patterns using spaCy's token attributes to 
        catch entities that the standard NER might miss.
        """
        found = []
        
        # Detect email addresses (using token attributes)
        for token in doc:
            # Email pattern: has @ symbol and dots
            if '@' in token.text and '.' in token.text.split('@')[1]:
                found.append({
                    "type": "EMAIL", 
                    "value": token.text
                })
        
        # Detect potential credit card numbers (sequences of digits with specific length)
        for i, token in enumerate(doc):
            if token.is_digit and 13 <= len(token.text) <= 19:
                found.append({
                    "type": "CREDIT_CARD",
                    "value": token.text
                })
            
            # Sequence of tokens that could form a credit card (with spaces/dashes)
            if i < len(doc) - 3 and token.is_digit:
                card_segment = ' '.join(t.text for t in doc[i:i+4] if t.is_digit or t.text in ['-', ' '])
                if card_segment.replace('-', '').replace(' ', '').isdigit():
                    if 13 <= len(card_segment.replace('-', '').replace(' ', '')) <= 19:
                        found.append({
                            "type": "CREDIT_CARD",
                            "value": card_segment
                        })
        
        return found
    
    def presidio_entity_detection(self, text: str) -> List[Dict[str, str]]:
        """
        Use Microsoft Presidio Analyzer to detect PII entities in the text.
        
        Presidio is specialized in detecting various types of personally identifiable
        information (PII) including different ID numbers, financial data, and more.
        
        Args:
            text: The input text to analyze
            
        Returns:
            A list of PII entities in the format {"type": entity_type, "value": entity_text}
        """
        # Entity type mapping: Presidio -> our standardized types
        PRESIDIO_ENTITY_MAP = {
            "PERSON": "PERSON_NAME",
            "PHONE_NUMBER": "PHONE",
            "EMAIL_ADDRESS": "EMAIL",
            "CREDIT_CARD": "CREDIT_CARD",
            "IBAN_CODE": "FINANCIAL",
            "IP_ADDRESS": "IP",
            "LOCATION": "LOCATION",
            "US_SSN": "SSN",
            "US_DRIVER_LICENSE": "ID_NUMBER",
            "US_PASSPORT": "ID_NUMBER",
            "US_BANK_NUMBER": "FINANCIAL",
            "CRYPTO": "FINANCIAL",
            "UK_NHS": "ID_NUMBER",
            "NRP": "ID_NUMBER",
            "DATE_TIME": "DATE",
            "URL": "URL",
            "ORGANIZATION": "COMPANY_NAME",
            "ADDRESS": "ADDRESS",
        }
        
        found = []
        
        # Analyze text with Presidio
        results = self.analyzer.analyze(
            text=text,
            language="en",
            entities=list(PRESIDIO_ENTITY_MAP.keys()),
            score_threshold=0.7  # Adjust confidence threshold as needed
        )
        
        # Process results
        for result in results:
            entity_text = text[result.start:result.end]
            if result.entity_type in PRESIDIO_ENTITY_MAP:
                entity_type = PRESIDIO_ENTITY_MAP[result.entity_type]
                found.append({
                    "type": entity_type,
                    "value": entity_text,
                    "confidence": result.score  # Presidio provides a confidence score
                })
                self.logger.debug(f"Presidio detected: {entity_text} as {entity_type} (score: {result.score:.2f})")
        
        # Remove confidence after using it for logging
        for entity in found:
            if "confidence" in entity:
                del entity["confidence"]
                
        return found
    
    def merge_entities(self, entities: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Merge entities from multiple detection methods, handling duplicates 
        and overlapping entities with priority rules.
        
        Args:
            entities: Combined list of entities from all detection methods
            
        Returns:
            Deduplicated and merged list of entities
        """
        # Group entities by their text value
        value_to_entities = {}
        
        for entity in entities:
            value = entity["value"]
            if value not in value_to_entities:
                value_to_entities[value] = []
            value_to_entities[value].append(entity)
        
        # Process each group of entities with the same value
        merged_entities = []
        for value, entity_group in value_to_entities.items():
            if len(entity_group) == 1:
                # Only one detection for this value
                merged_entities.append(entity_group[0])
            else:
                # Multiple detections for the same value
                # Apply priority rules based on specificity and detection method
                entity_types = [e["type"] for e in entity_group]
                
                # Priority order: specific entity types > general entity types
                priority_types = [
                    "SSN", "CREDIT_CARD", "EMAIL", "PHONE", "ADDRESS", 
                    "PERSON_NAME", "COMPANY_NAME", "FINANCIAL", "ID_NUMBER",
                    "LOCATION", "DATE", "URL", "IP", "NUMBER", "QUANTITY", "PRODUCT"
                ]
                
                # Find highest priority entity type that was detected
                chosen_type = None
                for p_type in priority_types:
                    if p_type in entity_types:
                        chosen_type = p_type
                        break
                
                # If no priority type found, use the most frequent type
                if not chosen_type:
                    from collections import Counter
                    type_counts = Counter(entity_types)
                    chosen_type = type_counts.most_common(1)[0][0]
                
                merged_entities.append({
                    "type": chosen_type,
                    "value": value
                })
        
        self.logger.debug(f"Merged {len(entities)} raw entities into {len(merged_entities)} unique entities")
        return merged_entities