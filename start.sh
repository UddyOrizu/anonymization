#!/bin/bash
# Simple startup script for the Anonymization API

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 to continue."
    exit 1
fi

echo "Starting Anonymization API..."

# Check if requirements are installed
if [ ! -f ".env_check" ]; then
    echo "First-time setup: Installing requirements..."
    python3 -m pip install -r requirements.txt
    
    echo "Downloading spaCy model..."
    python3 -m spacy download en_core_web_lg
    
    # Create a flag file to indicate setup has been done
    touch .env_check
fi

# Set environment variables
export PORT=8000
export HOST="0.0.0.0"
export RELOAD=true

# Start the server using the run script
echo "Starting server on http://localhost:$PORT"
python3 run.py

# Exit with the exit code from the Python script
exit $?
