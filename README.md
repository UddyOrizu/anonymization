# Anonymization API

This project provides a FastAPI-based web service for **text and document anonymization**. It uses advanced NLP techniques (spaCy, fastcoref, and Presidio) to detect and replace sensitive information such as names, organizations, emails, phone numbers, and various international identifiers.

---

## Features

- **Named Entity Recognition (NER):** Uses spaCy and fastcoref for entity extraction and coreference resolution.
- **Sensitive Data Detection:** Integrates Microsoft Presidio for robust detection of PII/PHI, including international IDs (passport, voter, SSN, etc.).
- **Anonymization:** Replaces detected entities with randomly generated or masked values, maintaining a mapping of original to anonymized values.
- **File Support:** Accepts plain text and DOCX files for anonymization.
- **API Endpoints:** Provides REST endpoints for both text and file anonymization.

---

## Endpoints

### `POST /anonymize/text`

Anonymizes sensitive entities in a text string.

**Request:**
- `text` (form field): The input text to anonymize.

**Response:**
- `anonymized_text`: The anonymized version of the input.
- `mapping`: Dictionary mapping original entities to their anonymized replacements.

---

### `POST /anonymize/file`

Anonymizes sensitive entities in an uploaded file (`.txt` or `.docx`).

**Request:**
- `file` (form field): The file to anonymize.

**Response:**
- `anonymized_text`: The anonymized content.
- `mapping`: Dictionary mapping original entities to their anonymized replacements.

---

## Supported Entities

- Names (PERSON)
- Organizations (ORG)
- Emails, Phone Numbers
- International IDs (passport, voter, SSN, NHS, etc.)
- Many more as defined in `PRESIDIO_ENTITIES`

---

## How It Works

1. **Entity Extraction:**  
   Uses spaCy NER and fastcoref for coreference resolution to extract entities from the text.

2. **Replacement Generation:**  
   For each entity, generates a random replacement (e.g., fake names, companies).

3. **Anonymization:**  
   - Replaces all occurrences of each entity with its replacement.
   - Uses Presidio Analyzer and Anonymizer for additional PII/PHI detection and masking.

4. **Mapping:**  
   Returns a mapping of original entities to their anonymized values.

---

## Setup

1. **Clone the repository and install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

2. **Download spaCy model:**
   ```sh
   python -m spacy download en_core_web_lg
   ```

3. **Run the API:**
   ```sh
   uvicorn main:app --reload
   ```

4. **Access the API docs:**  
   Visit [http://localhost:8000/docs](http://localhost:8000/docs) for interactive documentation.

---

## Example Usage

**Text anonymization:**
```sh
curl -X POST -F "text=John Doe works at Acme Corp. Email: john@example.com" http://localhost:8000/anonymize/text
```

**File anonymization:**
```sh
curl -X POST -F "file=@myfile.docx" http://localhost:8000/anonymize/file
```

---

## Notes

- Only `.txt` and `.docx` files are supported for file anonymization.
- The mapping in the response helps trace which original values were replaced.
- The system is extensible for additional entity types or custom anonymization logic.

---

## License

MIT License

---