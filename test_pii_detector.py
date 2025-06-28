import pytest
from security_pipeline.pipeline import PipelineContext
from security_pipeline.stages.PII_detector import PIIDetectorStage
from unittest.mock import patch, MagicMock


def test_regex_pii_detection():
    """Test the regex-based PII detection"""
    detector = PIIDetectorStage()
    
    # Test with sample text containing PII
    sample_text = """
    John Smith works at Acme Corporation.
    Contact him at john.smith@example.com or call 555-123-4567.
    His SSN is 123-45-6789 and IP address is 192.168.1.1.
    """
    
    entities = detector.regex_based_pii_detection(sample_text)
    
    # Check that entities were detected
    assert len(entities) > 0
    
    # Check for specific entity types
    entity_types = [entity["type"] for entity in entities]
    assert "EMAIL" in entity_types
    assert "PHONE" in entity_types
    assert "SSN" in entity_types
    assert "IP" in entity_types
    assert "PERSON_NAME" in entity_types
    assert "COMPANY_NAME" in entity_types


def test_spacy_entity_detection():
    """Test the spaCy-based entity detection"""
    detector = PIIDetectorStage()
    
    # Skip if spaCy is not available
    if not detector.spacy_available:
        pytest.skip("spaCy model not available")
    
    # Test with sample text
    sample_text = """
    Sarah Johnson is a researcher at Stanford University. 
    She visited New York City last April for a conference.
    The project received $50,000 in funding.
    """
    
    entities = detector.spacy_entity_detection(sample_text)
    
    # Check that entities were detected
    assert len(entities) > 0
    
    # Expected entity values (may vary slightly based on spaCy model)
    expected_values = ["Sarah Johnson", "Stanford University", "New York City", 
                      "April", "$50,000"]
    
    # Check that at least some of the expected entities were found
    detected_values = [entity["value"] for entity in entities]
    assert any(expected in detected_values for expected in expected_values)


def test_presidio_entity_detection():
    """Test the Presidio-based entity detection"""
    detector = PIIDetectorStage()
    
    # Skip if Presidio is not available
    if not detector.presidio_available:
        pytest.skip("Presidio Analyzer not available")
    
    # Test with sample text
    sample_text = """
    David Brown's credit card number is 4111-1111-1111-1111.
    His email is david.brown@company.org and he lives at 123 Main St, Seattle, WA.
    His passport number is 912803456 and his driver's license is DL9876543.
    """
    
    entities = detector.presidio_entity_detection(sample_text)
    
    # Check that entities were detected
    assert len(entities) > 0
    
    # Check for specific entity types (some may not be detected depending on Presidio version)
    entity_values = [entity["value"] for entity in entities]
    entity_types = [entity["type"] for entity in entities]
    
    # Test for some expected detections
    assert any("david.brown@company.org" in value for value in entity_values)
    assert any("4111-1111-1111-1111" in value for value in entity_values)
    assert any("EMAIL" in entity_type for entity_type in entity_types)
    assert any("PERSON_NAME" in entity_type for entity_type in entity_types)
    assert any("CREDIT_CARD" in entity_type for entity_type in entity_types)


def test_merge_entities():
    """Test the entity merging functionality"""
    detector = PIIDetectorStage()
    
    # Create overlapping entity detections
    entities = [
        {"type": "PERSON_NAME", "value": "John Smith"},
        {"type": "PERSON", "value": "John Smith"},  # Same value, different type
        {"type": "EMAIL", "value": "john@example.com"},
        {"type": "EMAIL", "value": "john@example.com"},  # Duplicate
        {"type": "PHONE", "value": "555-123-4567"},
        {"type": "CREDIT_CARD", "value": "4111111111111111"},
        {"type": "NUMBER", "value": "4111111111111111"}  # Same value as credit card
    ]
    
    merged = detector.merge_entities(entities)
    
    # Check that duplicates were merged
    assert len(merged) < len(entities)
    
    # Check that priority was respected (CREDIT_CARD should be chosen over NUMBER)
    cc_entity = next((e for e in merged if e["value"] == "4111111111111111"), None)
    assert cc_entity and cc_entity["type"] == "CREDIT_CARD"
    
    # Check that all unique values are preserved
    unique_values = {e["value"] for e in entities}
    merged_values = {e["value"] for e in merged}
    assert unique_values == merged_values


def test_pipeline_integration():
    """Test that the detector works within the pipeline context"""
    detector = PIIDetectorStage()
    
    # Test with sample text
    sample_text = """
    Jane Doe is a software engineer at TechCorp. 
    Her email is jane.doe@techcorp.com and phone number is 555-987-6543.
    """
    context = PipelineContext(original_text=sample_text)
    
    # Process through the pipeline
    result = detector.process(context)
    
    # Check that PII entities were added to context
    assert hasattr(result, "pii_entities")
    assert len(result.pii_entities) > 0
