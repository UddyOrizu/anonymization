import pytest
import os
from security_pipeline.pipeline import PipelineContext
from security_pipeline.stages.intent_classifier import IntentClassifierStage
from unittest.mock import patch


def test_keyword_intent_classification():
    """Test the keyword-based intent classification"""
    classifier = IntentClassifierStage()
    
    # Test search intent
    assert classifier.keyword_intent_classification("Find all emails from John") == "search"
    assert classifier.keyword_intent_classification("Show me customer records") == "search"
    assert classifier.keyword_intent_classification("Query the database for user info") == "search"
    
    # Test reasoning intent
    assert classifier.keyword_intent_classification("Why did the transaction fail?") == "reasoning"
    assert classifier.keyword_intent_classification("Explain the difference between reports") == "reasoning"
    assert classifier.keyword_intent_classification("How does this algorithm work?") == "reasoning"
    
    # Test ambiguous cases
    short_ambiguous = "Get analysis"  # Contains both search and reasoning keywords
    assert classifier.keyword_intent_classification(short_ambiguous) == "search"  # Should default to search due to length
    
    long_ambiguous = "Find the reasons why we should evaluate the search functionality of our query system and explain how it compares to other search engines"
    assert classifier.keyword_intent_classification(long_ambiguous) == "reasoning"  # Should choose reasoning due to length


def test_spacy_intent_classification():
    """Test the spaCy-based intent classification"""
    classifier = IntentClassifierStage()
    
    # Skip if spaCy model failed to load
    if classifier.nlp is None:
        pytest.skip("spaCy model not available")
    
    # Test search intent
    search_queries = [
        "Find all emails from John",
        "Show me customer records from last month",
        "I need to look up patient information",
        "Can you retrieve the latest sales data?"
    ]
    
    for query in search_queries:
        assert classifier.spacy_intent_classification(query) == "search"
    
    # Test reasoning intent
    reasoning_queries = [
        "Why did the transaction fail?",
        "How does this algorithm work?",
        "Can you explain how the system processes this data?",
        "What are the reasons for the decline in sales?"
    ]
    
    for query in reasoning_queries:
        assert classifier.spacy_intent_classification(query) == "reasoning"


def test_pipeline_integration():
    """Test that the classifier works within the pipeline context"""
    classifier = IntentClassifierStage()
    
    # Test with search query
    context = PipelineContext(original_text="Find all emails from John")
    result = classifier.process(context)
    assert result.intent == "search"
    
    # Test with reasoning query
    context = PipelineContext(original_text="Why did the transaction fail?")
    result = classifier.process(context)
    assert result.intent == "reasoning"


def test_llm_intent_classification():
    """Test the LLM-based intent classification with mocked responses"""
    classifier = IntentClassifierStage()
    
    # Skip if litellm is not available
    try:
        import litellm
    except ImportError:
        pytest.skip("litellm not available")
    
    # Patch the completion function to return predictable responses
    with patch('security_pipeline.stages.intent_classifier.completion') as mock_completion:
        # Mock a search response
        mock_completion.return_value.choices = [
            type('obj', (object,), {
                'message': type('obj', (object,), {'content': "search"})
            })
        ]
        
        # Test search intent
        assert classifier.llm_intent_classification("Find all emails from John") == "search"
        
        # Mock a reasoning response
        mock_completion.return_value.choices = [
            type('obj', (object,), {
                'message': type('obj', (object,), {'content': "reasoning"})
            })
        ]
        
        # Test reasoning intent
        assert classifier.llm_intent_classification("Why did the transaction fail?") == "reasoning"
        
        # Test error handling with unexpected response
        mock_completion.return_value.choices = [
            type('obj', (object,), {
                'message': type('obj', (object,), {'content': "unknown"})
            })
        ]
        
        # Should fall back to keyword classification
        with patch.object(classifier, 'keyword_intent_classification', return_value="fallback_result"):
            assert classifier.llm_intent_classification("Ambiguous query") == "fallback_result"
            

def test_llm_integration():
    """Test that the LLM classifier works with real API if available"""
    # This test only runs if explicitly enabled and API is available
    if not os.environ.get("TEST_LLM_INTEGRATION", "").lower() == "true":
        pytest.skip("LLM integration test disabled")
    
    classifier = IntentClassifierStage()
    # Force LLM usage for this test
    classifier.llm_config["use_llm"] = True
    
    # Test with search query
    try:
        result = classifier.llm_intent_classification("Find all emails from John")
        assert result in ["search", "reasoning"]
        
        # Test with reasoning query
        result = classifier.llm_intent_classification("Why did the transaction fail?")
        assert result in ["search", "reasoning"]
    except Exception as e:
        pytest.skip(f"LLM API not available: {str(e)}")

def test_ensemble_classification():
    """Test the ensemble classification approach with mocked results"""
    classifier = IntentClassifierStage()
    
    # Test case 1: All methods agree on "search"
    with patch.object(classifier, 'llm_intent_classification', return_value="search"), \
         patch.object(classifier, 'spacy_intent_classification', return_value="search"), \
         patch.object(classifier, 'keyword_intent_classification', return_value="search"):
        
        # Force LLM usage for this test
        classifier.llm_config["use_llm"] = True
        classifier.nlp = True  # Simulate spaCy being available
        
        context = PipelineContext(original_text="Find all emails from John")
        result = classifier.process(context)
        assert result.intent == "search"
    
    # Test case 2: All methods agree on "reasoning"
    with patch.object(classifier, 'llm_intent_classification', return_value="reasoning"), \
         patch.object(classifier, 'spacy_intent_classification', return_value="reasoning"), \
         patch.object(classifier, 'keyword_intent_classification', return_value="reasoning"):
        
        context = PipelineContext(original_text="Why did the transaction fail?")
        result = classifier.process(context)
        assert result.intent == "reasoning"
    
    # Test case 3: 2:1 majority for "search"
    with patch.object(classifier, 'llm_intent_classification', return_value="search"), \
         patch.object(classifier, 'spacy_intent_classification', return_value="search"), \
         patch.object(classifier, 'keyword_intent_classification', return_value="reasoning"):
        
        context = PipelineContext(original_text="Mixed intent query")
        result = classifier.process(context)
        assert result.intent == "search"
    
    # Test case 4: 2:1 majority for "reasoning"
    with patch.object(classifier, 'llm_intent_classification', return_value="reasoning"), \
         patch.object(classifier, 'spacy_intent_classification', return_value="reasoning"), \
         patch.object(classifier, 'keyword_intent_classification', return_value="search"):
        
        context = PipelineContext(original_text="Another mixed intent query")
        result = classifier.process(context)
        assert result.intent == "reasoning"
    
    # Test case 5: tie (1:1) with LLM failing
    with patch.object(classifier, 'llm_intent_classification', side_effect=Exception("LLM failed")), \
         patch.object(classifier, 'spacy_intent_classification', return_value="reasoning"), \
         patch.object(classifier, 'keyword_intent_classification', return_value="search"):
        
        context = PipelineContext(original_text="Tie with LLM failing")
        result = classifier.process(context)
        # In a tie, should use keyword result (search)
        assert result.intent == "search"
