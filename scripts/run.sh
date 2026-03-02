#!/usr/bin/env bash

if [ ! -d "venv" ]; then
    echo -e "Please create a virtual environment first.\nRun 'python -m venv venv'."
    exit 1
fi

if [ -z $VIRTUAL_ENV ]; then
    echo -e "Please activate the virtual environment first.\nRun 'source venv/bin/activate'."
    exit 1
fi

python -m pip install -r requirements.txt

# Load .env variables manually if needed, but python-dotenv in main.py does this too.
# export $(grep -v '^#' .env | xargs)

# Use waitress for cross-platform production stability (avoids fork issues on macOS)
python run_waitress.py
