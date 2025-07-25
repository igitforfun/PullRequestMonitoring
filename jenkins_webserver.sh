#!/bin/bash

# Define the virtual environment directory
VENV_DIR="venv"

activate_venv() {
    echo "Virtual environment found. Activating..."

    # Activate the virtual environment
    if [ -f "$VENV_DIR/Scripts/activate" ]; then
        # Windows
        source "$VENV_DIR/Scripts/activate"
    elif [ -f "$VENV_DIR/bin/activate" ]; then
        # macOS/Linux
        source "$VENV_DIR/bin/activate"
    else
        echo "Error: Unable to find the activation script in the virtual environment."
        exit 1
    fi

    echo "Virtual environment activated."
}

# Check if the virtual environment directory exists
if [ -d "$VENV_DIR" ]; then
    activate_venv
else
    python -m venv venv
    activate_venv
    pip install -r requirements.txt
fi
python ./cict_dashboard/cict_web.py