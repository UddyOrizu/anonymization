from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Tuple, List
from fastcoref import spacy_component
import spacy
import random
import string
import os
import re
from docx import Document
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

app = FastAPI(title="Anonymization API")

nlp = spacy.load("en_core_web_lg")
nlp.add_pipe("fastcoref")
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

ENTITY_LABELS = {
    "PERSON": "NAME",
    "ORG": "ORG",
}


PRESIDIO_ENTITIES = [
 'UK_NINO',
 'PHONE_NUMBER',
 'MEDICAL_LICENSE',
 'EMAIL_ADDRESS',
 'IN_VEHICLE_REGISTRATION',
 'CREDIT_CARD',
 'IBAN_CODE',
 'US_PASSPORT',
 'US_SSN',
 'IN_PASSPORT',
 'AU_ABN',
 'SG_NRIC_FIN',
 'AU_ACN',
 'US_BANK_NUMBER',
 'CRYPTO',
 'UK_NHS',
 'AU_TFN',
 'IP_ADDRESS',
 'IN_VOTER',
 'NRP',
 'US_DRIVER_LICENSE',
 'AU_MEDICARE',
 'US_ITIN']



def generate_random_person_name() -> str:
    """Generate a random person name."""
    first_names = [
        "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Jamie", "Avery", "Peyton", "Quinn","Abaobi"
    ]
    last_names = [
        "SmithDoe", "JohnsonDoe", "LeeDoe", "BrownDoe", "GarciaDoe", "MartinezDoe", "DavisDoe", "ClarkDoe", "LewisDoe", "WalkerDoe","OlufemiDoe"
    ]
    return f"{random.choice(first_names)} {random.choice(last_names)}"

def generate_random_company_name() -> str:
    """Generate a random company name."""
    prefixes = [
        "ABCTech", "ABCGlobal", "ABCNextGen", "XYZPioneer", "ABCVision", "ABCQuantum", "XYZBlue", "ABCGreen", "DEFPrime", "123Dynamic"
    ]
    suffixes = [
        "Solutions", "Systems", "Industries", "Enterprises", "Group", "Technologies", "Holdings", "Partners", "Labs", "Networks"
    ]
    return f"{random.choice(prefixes)} {random.choice(suffixes)}"


def extract_entities(text: str) -> List[Tuple[str, str]]:   
    # Use the resolved text for entity extraction
    doc = nlp(text)
    entities = []
    for ent in doc.ents:
        label = ENTITY_LABELS.get(ent.label_, None)
        if label:
            entities.append((ent.text, label))
    return list(set(entities))

def generate_replacement(entity_type: str) -> str:
    prefix = {
        "NAME": "Name",
        "ORG": "Org",
    }.get(entity_type, "Entity")
    rand_str = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    if entity_type == "ORG":
        return generate_random_company_name()
    elif entity_type == "NAME":
        return generate_random_person_name()
    else:
        return f"{prefix}_{rand_str}"

def anonymize_text(text: str) -> Tuple[str, Dict[str, str]]:
    resolve_doc = nlp(text,component_cfg={"fastcoref": {'resolve_text': True}})
    resolve_text = resolve_doc._.resolved_text
    print(f"Resolved Text: {resolve_text}")
    entities = extract_entities(resolve_text)
    mapping = {}
    for value, ent_type in entities:
        if value not in mapping:
            mapping[value] = generate_replacement(ent_type)
    anonymized = resolve_text
    # Replace entities, longest first, using regex with word boundaries
    for orig in sorted(mapping, key=len, reverse=False):
        anonymized = re.sub(r'\b{}\b'.format(re.escape(orig)), mapping[orig], anonymized)
    # Remove mapping entries not used in the final anonymized text
    used_mapping = {orig: repl for orig, repl in mapping.items() if repl in anonymized}
    
    anonymized, used_mapping = anonymize_text_presidio(anonymized, used_mapping)

    return anonymized, used_mapping
def anonymize_text_presidio(text: str,mapping: Dict[str, str]) -> Tuple[str, Dict[str, str]]:
    """
    Anonymize text using Presidio Analyzer and Anonymizer, maintaining mapping and replacement order.
    """
    
    # Analyze entities with Presidio
    results = analyzer.analyze(text=text, entities=PRESIDIO_ENTITIES, language="en")
    
    anonymized_result = anonymizer.anonymize(text=text,analyzer_results=results)
    anonymized_text = anonymized_result.text
    return anonymized_text, mapping

def read_file_content(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename)[1].lower()
    if ext in [".txt", ".md"]:
        return file.file.read().decode("utf-8")
    elif ext in [".docx"]:
        doc = Document(file.file)
        return "\n".join([p.text for p in doc.paragraphs])
    elif ext == ".doc":
        raise HTTPException(status_code=415, detail="DOC format not supported. Please use DOCX.")
    else:
        raise HTTPException(status_code=415, detail="Unsupported file type.")

@app.post("/anonymize/text")
async def anonymize_text_endpoint(text: str = Form(...)):
    anonymized, mapping = anonymize_text(text)
    return {"anonymized_text": anonymized, "mapping": mapping}

@app.post("/anonymize/file")
async def anonymize_file_endpoint(file: UploadFile = File(...)):
    try:
        content = read_file_content(file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    anonymized, mapping = anonymize_text(content)
    return {"anonymized_text": anonymized, "mapping": mapping}




