import pytest
from fastapi.testclient import TestClient
from main import app, generate_random_person_name, generate_random_company_name, generate_random_address, anonymize_text

client = TestClient(app)

def test_generate_random_person_name():
    name = generate_random_person_name()
    assert isinstance(name, str)
    assert len(name.split()) == 2

def test_generate_random_company_name():
    company = generate_random_company_name()
    assert isinstance(company, str)
    assert len(company.split()) == 2

def test_generate_random_address():
    address = generate_random_address()
    assert isinstance(address, str)
    assert "," in address


def test_anonymize_text_multiple():
    text = "John Doe works at Acme Corp. His email is john.doe@email.com and phone is +1-555-123-4567. John Doe also has a sister named Jane Doe. Jane works at Beta Inc. and she lives in Southampton,UK. you can reach John at email john.doe@email.com or call him at +1-555-123-4567"
    anonymized, mapping = anonymize_text(text)
    assert isinstance(anonymized, str)
    assert isinstance(mapping, dict)
    print("Anonymized Text:", anonymized)
    print("Mapping:", mapping)
    assert "John Doe" in mapping
    assert "Acme Corp." in mapping
    assert "john.doe@email.com" in mapping
    assert "1-555-123-4567" in mapping
    for orig, repl in mapping.items():
        assert orig not in anonymized
        assert repl in anonymized

def test_anonymize_text_simple():
    text = "John Doe works at Acme Corp. His email is john.doe@email.com and phone is +1-555-123-4567."
    anonymized, mapping = anonymize_text(text)
    print("Anonymized Text:", anonymized)
    print("Mapping:", mapping)
    assert isinstance(anonymized, str)
    assert isinstance(mapping, dict)
    assert "John Doe" in mapping
    assert "Acme Corp." in mapping
    assert "john.doe@email.com" in mapping
    assert "1-555-123-4567" in mapping
    for orig, repl in mapping.items():
        assert orig not in anonymized
        assert repl in anonymized

def test_anonymize_text_endpoint():
    response = client.post("/anonymize/text", data={"text": "Jane Smith from Widget Inc. lives in Springfield."})
    assert response.status_code == 200
    data = response.json()
    assert "anonymized_text" in data
    assert "mapping" in data
    assert "Jane Smith" in data["mapping"]
    assert "Widget Inc." in data["mapping"]

def test_anonymize_file_endpoint_txt(tmp_path):
    file_path = tmp_path / "test.txt"
    file_content = "Alice Johnson, alice@email.com, 123 Main St."
    file_path.write_text(file_content)
    with open(file_path, "rb") as f:
        response = client.post("/anonymize/file", files={"file": ("test.txt", f, "text/plain")})
    assert response.status_code == 200
    data = response.json()
    assert "Alice Johnson" in data["mapping"]
    assert "alice@email.com" in data["mapping"]
    assert "123 Main St." in data["mapping"] or "123 Main St." not in data["anonymized_text"]