# ---------------------------------------------------------------------------#
#                       STAGE 1: INTENT CLASSIFICATION                        #
# ---------------------------------------------------------------------------#
import logging
import os
from typing import Dict, Optional, Any
from security_pipeline.pipeline import PipelineContext, PipelineStage
import spacy
import numpy as np
import litellm
from litellm import completion


class IntentClassifierStage(PipelineStage):
    """
    Naïve keyword-based classifier for demo purposes.
    Swap out the logic (e.g., ML model) without changing the interface.
    """
    SEARCH_KEYWORDS = {
        "find", "lookup", "list", "search", "show", "retrieve", "query"
    }
    REASONING_KEYWORDS = {
        "why", "how", "explain", "compare", "analyse", "analysis",
        "reason", "evaluate", "calculate"
    }

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Configure LLM settings
        self.llm_config = {
            "model_name": os.environ.get("INTENT_MODEL", "ollama/gemma"),  # Default to ollama/gemma, but can be configured via env var
            "api_base": os.environ.get("OLLAMA_API_BASE", "http://localhost:11434"),  # Default Ollama API base
            "use_llm": os.environ.get("USE_LLM_INTENT", "true").lower() == "true"  # Whether to use LLM-based classification
        }
        
        # Check for Azure OpenAI configuration
        if "AZURE_OPENAI_API_KEY" in os.environ:
            self.logger.info("Azure OpenAI configuration detected")
            self.llm_config["model_name"] = os.environ.get("AZURE_OPENAI_MODEL", "gpt-4")
            self.llm_config["api_type"] = "azure"
            self.llm_config["api_version"] = os.environ.get("AZURE_OPENAI_API_VERSION", "2023-12-01-preview")
            self.llm_config["api_base"] = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
            self.llm_config["api_key"] = os.environ.get("AZURE_OPENAI_API_KEY", "")
            self.llm_config["use_llm"] = True
        
        # Initialize litellm for later use if configured
        if self.llm_config["use_llm"]:
            try:
                self.logger.info(f"Initializing LLM intent classifier with model: {self.llm_config['model_name']}")
            except Exception as e:
                self.logger.error(f"Error initializing LLM: {e}")
                self.llm_config["use_llm"] = False
        
        # Load spaCy model (as fallback)
        try:
            self.nlp = spacy.load("en_core_web_lg")
            self.logger.info("Successfully loaded spaCy model")
            
            # Define intent examples for training the classifier
            self.search_examples = [
                "Find all emails from John",
                "Show me customer records from last month",
                "Search for documents containing financial data",
                "List all transactions over $1000",
                "Query the database for user information",
                "Retrieve the latest sales figures",
                "Look up contact information for Jane Doe"
            ]
            
            self.reasoning_examples = [
                "Why did the transaction fail?",
                "How does this algorithm work?",
                "Explain the difference between these two reports",
                "Analyze the trends in this dataset",
                "Compare the performance of these two models",
                "What are the reasons for the decline in sales?",
                "Evaluate the effectiveness of our marketing strategy"
            ]
            
            # Generate vectors for examples
            self.search_vectors = [self.nlp(text).vector for text in self.search_examples]
            self.reasoning_vectors = [self.nlp(text).vector for text in self.reasoning_examples]
        except Exception as e:
            self.logger.error(f"Error loading spaCy model: {e}")
            # Fall back to keyword-based classification if model fails to load
            self.nlp = None

    def process(self, ctx: PipelineContext) -> PipelineContext:
        """
        Process text using an ensemble of classification methods.
        
        This method runs all available classification methods (LLM, spaCy, keyword)
        and uses majority voting to determine the final intent classification.
        If a method fails, it's excluded from voting.
        """
        # Initialize results dictionary to track votes
        results = {"search": 0, "reasoning": 0}
        methods_used = 0
        
        # 1. Try LLM-based classification
        if self.llm_config["use_llm"]:
            try:
                llm_intent = self.llm_intent_classification(ctx.original_text)
                results[llm_intent] += 1
                methods_used += 1
                self.logger.info(f"LLM classified intent as: {llm_intent}")
            except Exception as e:
                self.logger.error(f"LLM classification failed: {e}, excluding from ensemble")
        
        # 2. Try spaCy-based classification
        if self.nlp:
            try:
                spacy_intent = self.spacy_intent_classification(ctx.original_text)
                results[spacy_intent] += 1
                methods_used += 1
                self.logger.info(f"spaCy classified intent as: {spacy_intent}")
            except Exception as e:
                self.logger.error(f"spaCy classification failed: {e}, excluding from ensemble")
        
        # 3. Always use keyword-based classification (most reliable/simplest)
        keyword_intent = self.keyword_intent_classification(ctx.original_text)
        results[keyword_intent] += 1
        methods_used += 1
        self.logger.info(f"Keyword classified intent as: {keyword_intent}")
        
        # Determine final intent based on majority voting
        if methods_used == 0:
            # Fallback if somehow all methods failed
            ctx.intent = "search"  # Default to search as safer option
            self.logger.warning("All classification methods failed, defaulting to 'search'")
        elif results["search"] == results["reasoning"]:
            # In case of a tie, use more conservative approach (keyword)
            ctx.intent = keyword_intent
            self.logger.info(f"Tie in ensemble voting, using keyword method result: {keyword_intent}")
        else:
            # Select intent with most votes
            ctx.intent = "search" if results["search"] > results["reasoning"] else "reasoning"
            self.logger.info(f"Ensemble vote result - search: {results['search']}, reasoning: {results['reasoning']}")
        
        self.logger.debug(f"Final classified intent: {ctx.intent} (from {methods_used} methods)")
        
        return ctx

    def spacy_intent_classification(self, text: str) -> str:
        """
        Classify intent using spaCy's word embeddings.
        This method compares the input text vector against example vectors
        for search and reasoning intents to determine the closest match.
        """
        try:
            # Process text and get vector
            doc = self.nlp(text)
            query_vector = doc.vector
            
            # Calculate cosine similarity with search examples
            search_similarities = [
                np.dot(query_vector, ex_vector) / (np.linalg.norm(query_vector) * np.linalg.norm(ex_vector))
                for ex_vector in self.search_vectors
            ]
            
            # Calculate cosine similarity with reasoning examples
            reasoning_similarities = [
                np.dot(query_vector, ex_vector) / (np.linalg.norm(query_vector) * np.linalg.norm(ex_vector))
                for ex_vector in self.reasoning_vectors
            ]
            
            # Get the average similarity score for each intent
            avg_search_similarity = sum(search_similarities) / len(search_similarities)
            avg_reasoning_similarity = sum(reasoning_similarities) / len(reasoning_similarities)
            
            # Also consider verb pattern classification
            verb_based_intent = self._classify_by_verb_patterns(doc)
            
            # Calculate confidence scores (combining embedding similarity with verb patterns)
            search_confidence = avg_search_similarity + (0.3 if verb_based_intent == "search" else 0)
            reasoning_confidence = avg_reasoning_similarity + (0.3 if verb_based_intent == "reasoning" else 0)
            
            # Determine intent based on confidence scores
            intent = "search" if search_confidence > reasoning_confidence else "reasoning"
            
            self.logger.debug(f"spaCy intent classifier: search={search_confidence:.3f}, reasoning={reasoning_confidence:.3f}")
            return intent
            
        except Exception as e:
            self.logger.error(f"Error in spaCy intent classification: {e}")
            # Fall back to keyword-based classification
            return self.keyword_intent_classification(text)
    
    def _classify_by_verb_patterns(self, doc) -> str:
        """
        Helper method to classify intent based on verb usage patterns.
        """
        # Check for question words (strong indicators of reasoning)
        question_words = ["why", "how", "what", "when", "where", "which"]
        if any(token.text.lower() in question_words for token in doc[:3]):
            return "reasoning"
            
        # Look for verbs that indicate searching
        search_verbs = ["find", "search", "query", "retrieve", "list", "show", "get"]
        reasoning_verbs = ["explain", "analyze", "compare", "evaluate", "calculate", "determine"]
        
        for token in doc:
            if token.pos_ == "VERB":
                if token.lemma_.lower() in search_verbs:
                    return "search"
                if token.lemma_.lower() in reasoning_verbs:
                    return "reasoning"
        
        # Check for imperative statements (likely search)
        if len(doc) > 1 and doc[0].pos_ == "VERB":
            return "search"
        
        # Default to neutral
        return "neutral"

    def llm_intent_classification(self, text: str) -> str:
        """
        Classify intent using an LLM (via litellm) for more advanced understanding.
        
        This method uses litellm to support multiple LLM providers including:
        - Ollama (local models like gemma, llama, mistral)
        - Azure OpenAI
        - Others supported by litellm
        
        The classification is based on prompt engineering with clear instructions
        to determine if the query is a "search" or "reasoning" request.
        """
        # Create a prompt that clearly explains the task
        prompt = f"""You are an intent classifier. Your job is to identify if the query is asking for:
                    1) "search": Information retrieval, listing, finding data, looking up information, etc.
                    2) "reasoning": Explanations, analysis, comparisons, evaluations, etc.

                    Respond with ONLY the word "search" or "reasoning".

                    Examples of search queries:
                    - Find all emails from John
                    - Show me customer records from last month
                    - Search for documents containing financial data
                    - List all transactions over $1000

                    Examples of reasoning queries:
                    - Why did the transaction fail?
                    - How does this algorithm work?
                    - Explain the difference between these two reports
                    - Analyze the trends in this dataset

                    Query: {text}
                    Intent:"""

        try:
            # Make API call through litellm which handles the specific provider
            response = completion(
                model=self.llm_config["model_name"],
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,  # Use low temperature for deterministic responses
                max_tokens=10,    # We only need a short response
                api_base=self.llm_config.get("api_base"),
                api_key=self.llm_config.get("api_key", ""),
                api_version=self.llm_config.get("api_version", ""),
            )
            
            # Extract the intent from the response
            if response:
                result = response.choices[0].message.content.strip().lower()
                self.logger.debug(f"LLM raw response: {result}")
                
                # Normalize the response
                if "search" in result:
                    return "search"
                elif "reasoning" in result:
                    return "reasoning"
                else:
                    self.logger.warning(f"Unexpected LLM response: {result}, falling back to keyword-based")
                    return self.keyword_intent_classification(text)
            else:
                self.logger.warning("Empty response from LLM, falling back to keyword-based")
                return self.keyword_intent_classification(text)
                
        except Exception as e:
            self.logger.error(f"Error in LLM intent classification: {str(e)}")
            # Fall back to keyword-based classification
            return self.keyword_intent_classification(text)

    def keyword_intent_classification(self, text: str) -> str:
        """
        Process the input text to classify intent.
        This is a placeholder for more complex logic.
        """
        text_lower = text.lower()
        search_score = any(word in text_lower for word in self.SEARCH_KEYWORDS)
        reasoning_score = any(word in text_lower for word in self.REASONING_KEYWORDS)

        intent =""
        # Fallback to heuristic length check if ambiguous
        if search_score and not reasoning_score:
            intent = "search"
        elif reasoning_score and not search_score:
            intent = "reasoning"
        else:
            intent = "search" if len(text_lower) < 140 else "reasoning"  # heuristic
        
        self.logger.debug("Intent classified as '%s'", intent)
        return intent