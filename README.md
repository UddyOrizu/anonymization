# Anonymization API

This project provides a FastAPI-based web service for **text and document anonymization**. It uses advanced NLP techniques (spaCy, fastcoref, and Presidio) to detect and replace sensitive information such as names, organizations, emails, phone numbers, and various international identifiers.

---

## Features

- **Intent Classification:** 
  - Uses an ensemble approach with majority voting from multiple classifiers
  - Integrates LLMs (like Ollama Gemma, o3-mini, or Azure OpenAI) through litellm
  - Combines with spaCy embeddings and keyword-based classification
  - Provides robust intent classification through consensus decision making
- **PII Detection:**
  - Multi-approach entity detection combining regex patterns, spaCy NER, and Microsoft Presidio
  - Intelligent entity merging with prioritization of specific entity types
  - Comprehensive coverage of personal, financial, and location-based identifiers
- **Named Entity Recognition (NER):** Uses spaCy and fastcoref for entity extraction and coreference resolution.
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

Multi-approach detection for comprehensive coverage:

### Personal Information
- Names (PERSON_NAME)
- Email addresses (EMAIL)
- Phone numbers (PHONE)
- Physical addresses (ADDRESS)

### Financial Information
- Credit card numbers (CREDIT_CARD)
- Banking details (FINANCIAL)
- Currency amounts (FINANCIAL)
- Cryptocurrency addresses (FINANCIAL)

### Identification Documents
- Social Security Numbers (SSN)
- Passport numbers (ID_NUMBER)
- Driver's license numbers (ID_NUMBER)
- National health IDs (ID_NUMBER)

### Digital Identifiers
- IP addresses (IP)
- URLs (URL)

### Organizations & Locations
- Company names (COMPANY_NAME)
- Organizations (COMPANY_NAME)
- Geographic locations (LOCATION)
- Countries, cities, states (LOCATION)

### Temporal Information
- Dates (DATE)
- Times (TIME)

---

## How It Works

1. **Intent Classification:**  
   - Uses an ensemble approach with majority voting from three different classifiers:
     - LLMs via litellm (supporting Ollama models, Azure OpenAI, etc.)
     - spaCy word embeddings for semantic similarity comparison
     - Keyword-based heuristic classification
   - Combines results using a democratic voting system where highest vote wins
   - Handles ties and failures gracefully with fallback mechanisms
   - Categorizes user queries as either "search" or "reasoning" intents
   - Can be configured via environment variables (MODEL_NAME, USE_LLM_INTENT, etc.)

2. **PII Detection:**  
   - Employs multiple methods for comprehensive entity detection:
     - Pattern-based detection using regular expressions
     - NER-based detection using spaCy's pre-trained models
     - Specialized PII detection using Microsoft Presidio
   - Merges results with intelligent prioritization of entity types
   - Handles overlapping and duplicate entities

3. **Entity Extraction:**  
   Uses spaCy NER and fastcoref for coreference resolution to extract entities from the text.

4. **Replacement Generation:**  
   For each entity, generates a random replacement (e.g., fake names, companies).

5. **Anonymization:**  
   - Replaces all occurrences of each entity with its replacement.
   - Uses Presidio Anonymizer for PII/PHI masking with appropriate formats.

5. **Mapping:**  
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

3. **Optional: Set up Ollama for LLM-based intent classification:**
   ```sh
   # Install Ollama if not already installed
   # Then pull a model (example: gemma)
   ollama pull gemma
   ```

4. **Configure environment variables (optional):**
   ```sh
   # For Ollama-based intent classification
   export USE_LLM_INTENT=true
   export INTENT_MODEL=ollama/gemma
   export OLLAMA_API_BASE=http://localhost:11434
   
   # For Azure OpenAI (alternative)
   export USE_LLM_INTENT=true
   export AZURE_OPENAI_API_KEY=your_api_key
   export AZURE_OPENAI_ENDPOINT=your_endpoint
   export AZURE_OPENAI_MODEL=your_model_deployment_name
   ```

5. **Run the API:**
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