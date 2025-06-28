import logging
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Tuple
from security_pipeline.pipeline import SecurityPipeline
from security_pipeline.stages.PII_detector import PIIDetectorStage
from security_pipeline.stages.PII_masking import PIIMaskStage
from security_pipeline.stages.audit_trail import AuditStage
from security_pipeline.stages.corefrence import CoreferenceStage
from security_pipeline.stages.intent_classifier import IntentClassifierStage
from security_pipeline.stages.name_replacement import NameReplacementStage
import os
from docx import Document


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("anonymization_api")

app = FastAPI(title="Anonymization API")


@app.on_event("startup")
async def startup_event():
    """
    Verify that all components are properly initialized on startup.
    This helps catch configuration issues early.
    """
    logger.info("Starting Anonymization API")
    try:
        # Test pipeline initialization
        test_pipeline = build_default_pipeline()
        logger.info("Pipeline initialized successfully with %d stages", len(test_pipeline.stages))
        
        # Log the available stages
        stage_names = [stage.__class__.__name__ for stage in test_pipeline.stages]
        logger.info("Pipeline stages: %s", ", ".join(stage_names))
        
    except Exception as e:
        logger.error("Failed to initialize pipeline: %s", str(e))
        logger.exception("Detailed error:")


# ---------------------------------------------------------------------------#
#                       DEFAULT PIPELINE FACTORY                             #
# ---------------------------------------------------------------------------#
def build_default_pipeline() -> SecurityPipeline:
    """
    Returns a pre-configured pipeline that fulfils the spec:
        • Intent → PII detect → mask → replace → audit
    """
    return SecurityPipeline(
        stages=[            
            IntentClassifierStage(),
            CoreferenceStage(),
            PIIDetectorStage(),
            PIIMaskStage(),
            NameReplacementStage(),
            AuditStage(),
        ]
    )

def anonymize_text(text: str) -> Tuple[str,str,Dict[str, str]]:    
    try:
        pipeline = build_default_pipeline()
        result = pipeline.process(text)
        print(f"Processed text: {result}")
        return result.processed_text, result.intent, result.replacement_map
    except Exception as e:
        logger.error("Error processing text: %s", str(e))
        logger.exception("Detailed error:")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

  

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

@app.get("/")
async def root():
    """
    Root endpoint providing API information and documentation links.
    """
    return {
        "name": "Anonymization API",
        "version": "1.0.0",
        "description": "API for anonymizing text and documents containing PII",
        "documentation": "/docs",
        "healthCheck": "/health"
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify the API is running correctly.
    Attempts to initialize the pipeline to ensure dependencies are working.
    """
    try:
        test_pipeline = build_default_pipeline()
        return {
            "status": "healthy",
            "pipeline_stages": len(test_pipeline.stages),
            "stage_names": [stage.__class__.__name__ for stage in test_pipeline.stages]
        }
    except Exception as e:
        logger.error("Health check failed: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )

@app.post("/anonymize/text")
async def anonymize_text_endpoint(text: str = Form(...)):
    """
    Anonymize sensitive entities in a text string.
    
    Args:
        text: The input text to anonymize
        
    Returns:
        JSON with anonymized text, detected intent, and mapping of replacements
    """
    anonymized, intent, mapping = anonymize_text(text)
    return {"anonymized_text": anonymized, "intent": intent, "mapping": mapping}

@app.post("/anonymize/file")
async def anonymize_file_endpoint(file: UploadFile = File(...)):
    """
    Anonymize sensitive entities in an uploaded file (txt or docx).
    
    Args:
        file: The file to anonymize
        
    Returns:
        JSON with anonymized text, detected intent, and mapping of replacements
    """
    try:
        content = read_file_content(file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    anonymized, intent, mapping = anonymize_text(content)
    return {"anonymized_text": anonymized, "intent": intent, "mapping": mapping}





# ---------------------------------------------------------------------------#
#                           DEMO / UNIT TEST                                 #
# ---------------------------------------------------------------------------#
if __name__ == "__main__":
    """
    Simple demo usage when script is run directly.
    For production deployment, use the run.py script or uvicorn directly.
    """
    import uvicorn
    
    demo_text = (
        "Please explain why John Smith from Acme Corp sent 123 Main Street "
        "New York an email at john.smith@example.com regarding invoice "
        "4000-1234-5678-9111 and call him on (212) 555-1234."
    )
    
    logger.info("Demo text: %s", demo_text)
    
    try:
        # Test anonymization
        anonymized, intent, mapping = anonymize_text(demo_text)
        logger.info("Anonymized text: %s", anonymized)
        logger.info("Intent: %s", intent)
        logger.info("Mapping: %s", mapping)
        
        # Start development server
        logger.info("Starting development server at http://127.0.0.1:8000")
        uvicorn.run(app, host="127.0.0.1", port=8000)
    except Exception as e:
        logger.error("Failed to run demo: %s", str(e))
        logger.exception("Detailed error:")

