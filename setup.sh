#!/bin/bash
cd /home/rue/projects/testcase-generator
source .venv/bin/activate
pip install fastapi uvicorn openai python-docx openpyxl aiosqlite python-multipart pydantic pydantic-settings 2>&1
echo "=== DONE ==="
python3 -c "import fastapi, uvicorn, openai, docx, openpyxl, aiosqlite; print('All imports OK!')"
