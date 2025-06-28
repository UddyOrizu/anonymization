#!/usr/bin/env python3
"""
Run script for the Anonymization API.
This script starts the FastAPI application using uvicorn with proper configuration.
"""
import os
import sys
import logging
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("run_api")

def main():
    """Start the Anonymization API server"""
    try:
        # Check if required packages are installed
        import fastapi
        import spacy
        
        # Check if spaCy model is available
        try:
            spacy.load("en_core_web_lg")
            logger.info("spaCy model loaded successfully")
        except Exception as e:
            logger.error("Failed to load spaCy model: %s", str(e))
            logger.info("Try running: python -m spacy download en_core_web_lg")
            return 1
        
        # Get configuration from environment
        port = int(os.environ.get("PORT", 8000))
        host = os.environ.get("HOST", "0.0.0.0")
        reload = os.environ.get("RELOAD", "").lower() == "true"
        
        logger.info("Starting Anonymization API on %s:%d (reload=%s)", host, port, reload)
        
        # Start server
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info",
        )
        
        return 0
    except ImportError as e:
        logger.error("Missing required package: %s", str(e))
        logger.info("Try running: pip install -r requirements.txt")
        return 1
    except Exception as e:
        logger.error("Failed to start server: %s", str(e))
        logger.exception("Detailed error:")
        return 1

if __name__ == "__main__":
    sys.exit(main())
