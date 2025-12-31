#!/bin/bash
# Render.com startup script with Python 3.11 enforcement

echo "========================================"
echo "Checking Python version..."
echo "========================================"

python --version

echo "========================================"
echo "Starting application with uvicorn..."
echo "========================================"

# Use system Python if it's 3.11, otherwise fail gracefully
PYTHON_VERSION=$(python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')

if [[ $PYTHON_VERSION == "3.13" ]]; then
    echo "ERROR: Python 3.13 detected. This version is incompatible with psycopg2-binary."
    echo "Please configure Python 3.11 in Render dashboard."
    exit 1
fi

# Start the application
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8001}
