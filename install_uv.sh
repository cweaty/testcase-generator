#!/bin/bash
set -e
cd /home/rue/projects/testcase-generator
source .venv/bin/activate
echo "Installing uvicorn..."
pip install uvicorn h11 click 2>&1 || python3 -m pip install uvicorn h11 click 2>&1
echo "Testing imports..."
python3 test_imports.py
